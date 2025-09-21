# app/crud/analytics_queries.py
from __future__ import annotations

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta, timezone
import time

from sqlalchemy.orm import Session
from sqlalchemy import case, and_, func, literal, text, bindparam, or_

from app.models.moodle import (
    MdlGradeGrades,
    MdlGradeItems,
    MdlCourse,
    MdlUser,
    MdlCourseCategories,
)

# -------------------------------------------------------------------
# Constants
# -------------------------------------------------------------------
RISK_THRESHOLD_DEFAULT = 50


# -------------------------------------------------------------------
# Basic KPIs used by the charts
# -------------------------------------------------------------------
def get_total_notes(db: Session) -> int:
    """Total de notas con finalgrade NO nulo."""
    return int(
        db.query(func.count(MdlGradeGrades.id))
        .filter(MdlGradeGrades.finalgrade.isnot(None))
        .scalar()
        or 0
    )


def get_notes_by_status(db: Session) -> Dict[str, int]:
    """Conteo por estado (PASSED, FAILED, ABSENT)."""
    # ABSENT = finalgrade is NULL
    absent_count = int(
        db.query(func.count(MdlGradeGrades.id))
        .filter(MdlGradeGrades.finalgrade.is_(None))
        .scalar()
        or 0
    )

    # PASSED vs FAILED (solo con finalgrade)
    status_rows = (
        db.query(
            case(
                (MdlGradeGrades.finalgrade >= MdlGradeItems.gradepass, "PASSED"),
                else_="FAILED",
            ).label("status"),
            func.count(MdlGradeGrades.id).label("count"),
        )
        .join(MdlGradeItems, MdlGradeGrades.itemid == MdlGradeItems.id)
        .filter(MdlGradeGrades.finalgrade.isnot(None))
        .group_by("status")
        .all()
    )

    out = {"PASSED": 0, "FAILED": 0, "ABSENT": absent_count}
    for status, count in status_rows:
        if status in out:
            out[status] = int(count or 0)
    return out


def get_notes_by_status_over_time(db: Session, period: str = "month") -> List[Dict[str, Any]]:
    """
    Conteo por estado agrupado por período.
    Si period='month' => YYYY-MM, si no => YYYY-MM-DD.
    """
    date_format_str = "%Y-%m" if period == "month" else "%Y-%m-%d"

    status_subq = (
        db.query(
            MdlGradeGrades.id,
            func.DATE_FORMAT(
                func.FROM_UNIXTIME(MdlGradeGrades.timemodified), date_format_str
            ).label("period"),
            case(
                (MdlGradeGrades.finalgrade.is_(None), "ABSENT"),
                (MdlGradeGrades.finalgrade >= MdlGradeItems.gradepass, "PASSED"),
                else_="FAILED",
            ).label("status"),
        )
        .join(MdlGradeItems, MdlGradeGrades.itemid == MdlGradeItems.id)
        .filter(MdlGradeGrades.timemodified.isnot(None))
        .subquery()
    )

    rows = (
        db.query(
            status_subq.c.period,
            status_subq.c.status,
            func.count().label("count"),
        )
        .group_by(status_subq.c.period, status_subq.c.status)
        .order_by(status_subq.c.period, status_subq.c.status)
        .all()
    )

    bucket: Dict[str, Dict[str, Any]] = {}
    for p, st, cnt in rows:
        bucket.setdefault(p, {"period": p, "PASSED": 0, "FAILED": 0, "ABSENT": 0})
        if st in bucket[p]:
            bucket[p][st] = int(cnt or 0)

    return list(bucket.values())


def get_course_details_for_month(
    db: Session, month: str, limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Detalle por curso para un mes (YYYY-MM): PASSED/FAILED/ABSENT.
    Devuelve ordenado por total desc y respeta el limit.
    """
    date_format_str = "%Y-%m"

    status_subq = (
        db.query(
            MdlGradeGrades.id,
            MdlGradeItems.courseid,
            case(
                (MdlGradeGrades.finalgrade.is_(None), "ABSENT"),
                (MdlGradeGrades.finalgrade >= MdlGradeItems.gradepass, "PASSED"),
                else_="FAILED",
            ).label("status"),
        )
        .join(MdlGradeItems, MdlGradeGrades.itemid == MdlGradeItems.id)
        .filter(
            func.DATE_FORMAT(
                func.FROM_UNIXTIME(MdlGradeGrades.timemodified), date_format_str
            )
            == month
        )
        .subquery()
    )

    # Orden por total de notas desc y limit
    course_totals_q = (
        db.query(
            MdlCourse.fullname.label("course_name"),
            func.count().label("total_count"),
        )
        .join(status_subq, MdlCourse.id == status_subq.c.courseid)
        .group_by(MdlCourse.fullname)
        .order_by(func.count().desc())
    )
    if limit:
        course_totals_q = course_totals_q.limit(int(limit))

    ordered_names = [r.course_name for r in course_totals_q.all()]
    if not ordered_names:
        return []

    rows = (
        db.query(
            MdlCourse.fullname.label("course_name"),
            status_subq.c.status,
            func.count().label("count"),
        )
        .join(status_subq, MdlCourse.id == status_subq.c.courseid)
        .filter(MdlCourse.fullname.in_(ordered_names))
        .group_by(MdlCourse.fullname, status_subq.c.status)
        .order_by(MdlCourse.fullname, status_subq.c.status)
        .all()
    )

    by_course: Dict[str, Dict[str, Any]] = {}
    for cname, st, cnt in rows:
        by_course.setdefault(
            cname, {"course_name": cname, "PASSED": 0, "FAILED": 0, "ABSENT": 0}
        )
        if st in by_course[cname]:
            by_course[cname][st] = int(cnt or 0)

    return [by_course[n] for n in ordered_names if n in by_course]


# -------------------------------------------------------------------
# Failure / Absence buckets (+ drill-down)
# -------------------------------------------------------------------
def _grade_status_subquery(db: Session):
    """Subconsulta (userid, courseid, status) con itemtype='mod'."""
    return (
        db.query(
            MdlGradeGrades.userid.label("userid"),
            MdlGradeItems.courseid.label("courseid"),
            case(
                (MdlGradeGrades.finalgrade.is_(None), "ABSENT"),
                (MdlGradeGrades.finalgrade < MdlGradeItems.gradepass, "FAILED"),
                else_="PASSED",
            ).label("status"),
        )
        .join(MdlGradeItems, MdlGradeGrades.itemid == MdlGradeItems.id)
        .filter(MdlGradeItems.itemtype == "mod")
        .subquery()
    )


def _user_course_status_counts(db: Session):
    """
    (userid, courseid, failed_count, absent_count) por alumno-curso.
    """
    gs = _grade_status_subquery(db)
    return (
        db.query(
            gs.c.userid.label("userid"),
            gs.c.courseid.label("courseid"),
            func.count(case((gs.c.status == "FAILED", 1))).label("failed_count"),
            func.count(case((gs.c.status == "ABSENT", 1))).label("absent_count"),
        )
        .group_by(gs.c.userid, gs.c.courseid)
        .subquery()
    )


def get_failure_absence_analytics(db: Session) -> Dict[str, int]:
    """
    Buckets (todos por 'mismo curso', usando (userid, courseid)):
      - fail_1_same_course
      - fail_2_same_course
      - fail_gt_2_same_course
      - absent_1_same_course
      - absent_2_same_course
      - absent_1_fail_1_same_course
      - absent_gt_1_fail_gt_1_same_course
    """
    ucc = _user_course_status_counts(db)

    def count_where(expr) -> int:
        return int(db.query(func.count()).select_from(ucc).filter(expr).scalar() or 0)

    return {
        "fail_1_same_course": count_where(ucc.c.failed_count == 1),
        "fail_2_same_course": count_where(ucc.c.failed_count == 2),
        "fail_gt_2_same_course": count_where(ucc.c.failed_count > 2),
        "absent_1_same_course": count_where(ucc.c.absent_count == 1),
        "absent_2_same_course": count_where(ucc.c.absent_count == 2),
        "absent_1_fail_1_same_course": count_where(
            and_(ucc.c.absent_count == 1, ucc.c.failed_count == 1)
        ),
        "absent_gt_1_fail_gt_1_same_course": count_where(
            and_(ucc.c.absent_count > 1, ucc.c.failed_count > 1)
        ),
    }


def get_bucket_details(db: Session, bucket: str) -> List[Dict[str, Any]]:
    """
    Filas por alumno-curso para el bucket solicitado.
    Cada fila: user_id, firstname, lastname, email, course_id, course_name, failed_count, absent_count
    """
    # 1) Per-grade status
    grade_status_sq = (
        db.query(
            MdlGradeGrades.userid.label("userid"),
            MdlGradeItems.courseid.label("courseid"),
            case(
                (MdlGradeGrades.finalgrade.is_(None), "ABSENT"),
                (MdlGradeGrades.finalgrade < MdlGradeItems.gradepass, "FAILED"),
                else_="PASSED",
            ).label("status"),
        )
        .join(MdlGradeItems, MdlGradeGrades.itemid == MdlGradeItems.id)
        .filter(MdlGradeItems.itemtype == "mod")
        .subquery()
    )

    # 2) Per-user, per-course aggregates
    user_course_counts = (
        db.query(
            grade_status_sq.c.userid,
            grade_status_sq.c.courseid,
            func.count(case((grade_status_sq.c.status == "FAILED", 1))).label(
                "failed_count"
            ),
            func.count(case((grade_status_sq.c.status == "ABSENT", 1))).label(
                "absent_count"
            ),
        )
        .group_by(grade_status_sq.c.userid, grade_status_sq.c.courseid)
        .subquery()
    )

    # 3) Bucket filters
    filters = {
        "fail_1_same_course": user_course_counts.c.failed_count == 1,
        "fail_2_same_course": user_course_counts.c.failed_count == 2,
        "fail_gt_2_same_course": user_course_counts.c.failed_count > 2,
        "absent_1_same_course": user_course_counts.c.absent_count == 1,
        "absent_2_same_course": user_course_counts.c.absent_count == 2,
        "absent_1_fail_1_same_course": and_(
            user_course_counts.c.absent_count == 1,
            user_course_counts.c.failed_count == 1,
        ),
        "absent_gt_1_fail_gt_1_same_course": and_(
            user_course_counts.c.absent_count > 1,
            user_course_counts.c.failed_count > 1,
        ),
    }
    condition = filters.get(bucket)
    if condition is None:
        return []

    # 4) Join user + course to include names/emails + course_name
    rows = (
        db.query(
            user_course_counts.c.userid.label("user_id"),
            MdlUser.firstname,
            MdlUser.lastname,
            MdlUser.email,
            user_course_counts.c.courseid.label("course_id"),
            MdlCourse.fullname.label("course_name"),
            user_course_counts.c.failed_count,
            user_course_counts.c.absent_count,
        )
        .join(MdlUser, MdlUser.id == user_course_counts.c.userid)
        .join(MdlCourse, MdlCourse.id == user_course_counts.c.courseid)
        .filter(condition)
        .order_by(
            MdlCourse.fullname.asc(),
            MdlUser.lastname.asc(),
            MdlUser.firstname.asc(),
        )
        .all()
    )

    return [
        {
            "user_id": r.user_id,
            "firstname": r.firstname,
            "lastname": r.lastname,
            "email": r.email,
            "course_id": r.course_id,
            "course_name": r.course_name,
            "failed_count": int(r.failed_count or 0),
            "absent_count": int(r.absent_count or 0),
        }
        for r in rows
    ]


# -------------------------------------------------------------------
# Predictive helpers (risk score, series, heatmap, details)
# -------------------------------------------------------------------
def _risk_score(failed_count: int, absent_count: int) -> int:
    """
    Simple y explicable: penaliza reprobados y ausentes.
    """
    score = failed_count * 35 + absent_count * 25
    if failed_count > 0 and absent_count > 0:
        score += 10  # interacción
    return int(min(100, score))


def _risk_score_expr(failed_col, absent_col):
    """
    SQLAlchemy expression version of the risk score:
      35*failed + 25*absent + 10 if both > 0
    Works inside SUM/CASE without Python-side branching.
    """
    return (
        failed_col * literal(35)
        + absent_col * literal(25)
        + case((and_(failed_col > 0, absent_col > 0), literal(10)), else_=literal(0))
    )


def _bucket_label(failed_count: int, absent_count: int) -> str:
    if failed_count >= 2 and absent_count >= 2:
        return "absent>1_fail>1_same_course"
    if failed_count == 1 and absent_count == 1:
        return "absent_1_fail_1_same_course"
    if failed_count > 2:
        return "fail_gt_2_same_course"
    if failed_count == 2:
        return "fail_2_same_course"
    if failed_count == 1:
        return "fail_1_same_course"
    if absent_count > 2:
        return "absent_gt_2_same_course"
    if absent_count == 2:
        return "absent_2_same_course"
    if absent_count == 1:
        return "absent_1_same_course"
    return "ok"


def _grade_status_with_period(db: Session, date_format: str = "%Y-%m"):
    """
    Subconsulta con columnas: userid, courseid, period, status in {PASSED, FAILED, ABSENT}
    """
    return (
        db.query(
            MdlGradeGrades.userid.label("userid"),
            MdlGradeItems.courseid.label("courseid"),
            func.DATE_FORMAT(
                func.FROM_UNIXTIME(MdlGradeGrades.timemodified), date_format
            ).label("period"),
            case(
                (MdlGradeGrades.finalgrade.is_(None), "ABSENT"),
                (MdlGradeGrades.finalgrade < MdlGradeItems.gradepass, "FAILED"),
                else_="PASSED",
            ).label("status"),
        )
        .join(MdlGradeItems, MdlGradeGrades.itemid == MdlGradeItems.id)
        .filter(MdlGradeItems.itemtype == "mod")
        .filter(MdlGradeGrades.timemodified.isnot(None))
        .subquery()
    )


def _user_course_agg(db: Session):
    """
    Agrega (todo el tiempo) por (user, course):
      failed_count, absent_count, last_period
    """
    status_sq = _grade_status_with_period(db)

    # último período por (user, course)
    last_period_sq = (
        db.query(
            status_sq.c.userid,
            status_sq.c.courseid,
            func.max(status_sq.c.period).label("last_period"),
        )
        .group_by(status_sq.c.userid, status_sq.c.courseid)
        .subquery()
    )

    agg = (
        db.query(
            status_sq.c.userid,
            status_sq.c.courseid,
            func.count(case((status_sq.c.status == "FAILED", 1))).label(
                "failed_count"
            ),
            func.count(case((status_sq.c.status == "ABSENT", 1))).label(
                "absent_count"
            ),
            last_period_sq.c.last_period,
        )
        .join(
            last_period_sq,
            and_(
                last_period_sq.c.userid == status_sq.c.userid,
                last_period_sq.c.courseid == status_sq.c.courseid,
            ),
        )
        .group_by(
            status_sq.c.userid, status_sq.c.courseid, last_period_sq.c.last_period
        )
        .subquery()
    )
    return agg


def _user_course_period_agg(db: Session, months_back: int = 12):
    """
    Agrega por (user, course, period): failed_count, absent_count
    (Se puede recortar por meses si se agrega filtro de fechas aguas arriba).
    """
    status_sq = _grade_status_with_period(db)

    agg = (
        db.query(
            status_sq.c.userid,
            status_sq.c.courseid,
            status_sq.c.period,
            func.count(case((status_sq.c.status == "FAILED", 1))).label(
                "failed_count"
            ),
            func.count(case((status_sq.c.status == "ABSENT", 1))).label(
                "absent_count"
            ),
        )
        .group_by(status_sq.c.userid, status_sq.c.courseid, status_sq.c.period)
        .subquery()
    )
    return agg


def get_risk_by_course(
    db: Session, min_score: int = RISK_THRESHOLD_DEFAULT, limit: int = 12
) -> List[Dict[str, Any]]:
    agg = _user_course_agg(db)

    score = _risk_score_expr(agg.c.failed_count, agg.c.absent_count)

    rows = (
        db.query(
            agg.c.courseid.label("course_id"),
            MdlCourse.fullname.label("course_name"),
            func.sum(case((score >= min_score, 1), else_=0)).label("at_risk_count"),
            func.count().label("total_pairs"),
        )
        .join(MdlCourse, MdlCourse.id == agg.c.courseid)
        .group_by(agg.c.courseid, MdlCourse.fullname)
        .order_by(func.sum(case((score >= min_score, 1), else_=0)).desc())
        .limit(limit)
        .all()
    )

    results = []
    for r in rows:
        total_learners = (
            db.query(func.count(func.distinct(agg.c.userid)))
            .filter(agg.c.courseid == r.course_id)
            .scalar()
        ) or 0
        at_risk_count = int(r.at_risk_count or 0)
        total_pairs = int(r.total_pairs or 0)
        risk_rate = (at_risk_count / total_pairs) if total_pairs else 0.0
        results.append(
            {
                "course_id": r.course_id,
                "course_name": r.course_name,
                "at_risk_count": at_risk_count,
                "total_learners": int(total_learners),
                "risk_rate": round(risk_rate, 4),
            }
        )
    return results


def get_risk_time_series(
    db: Session,
    min_score: int = RISK_THRESHOLD_DEFAULT,
    months_back: int = 12,
    include_forecast: bool = True,
    forecast_horizon: int = 3,
) -> List[Dict[str, Any]]:
    per = _user_course_period_agg(db, months_back=months_back)
    score = _risk_score_expr(per.c.failed_count, per.c.absent_count)
    rows = (
        db.query(
            per.c.period,
            func.sum(case((score >= min_score, 1), else_=0)).label("at_risk_count")
        )
        .group_by(per.c.period)
        .order_by(per.c.period)
        .all()
    )

    series = [
        {"period": r.period, "at_risk_count": int(r.at_risk_count or 0), "is_forecast": False}
        for r in rows
    ]

    if include_forecast and series:
        # Simple MA(3)
        values = [p["at_risk_count"] for p in series][-3:]
        avg = int(round(sum(values) / len(values))) if values else 0

        def next_period(p: str) -> str:
            y, m = map(int, p.split("-"))
            m += 1
            if m > 12:
                m = 1
                y += 1
            return f"{y:04d}-{m:02d}"

        last = series[-1]["period"]
        cur = last
        for _ in range(forecast_horizon):
            cur = next_period(cur)
            series.append({"period": cur, "at_risk_count": avg, "is_forecast": True})

    return series


def get_risk_heatmap(
    db: Session,
    min_score: int = RISK_THRESHOLD_DEFAULT,
    months_back: int = 6,
    top_courses: int = 20,
) -> List[Dict[str, Any]]:
    per = _user_course_period_agg(db, months_back=months_back)
    score = _risk_score_expr(per.c.failed_count, per.c.absent_count)

    totals = (
        db.query(
            per.c.courseid.label("course_id"),
            func.sum(case((score >= min_score, 1), else_=0)).label("risk_total")
        )
        .group_by(per.c.courseid)
        .order_by(func.sum(case((score >= min_score, 1), else_=0)).desc())
        .limit(top_courses)
        .subquery()
    )

    rows = (
        db.query(
            per.c.courseid.label("course_id"),
            MdlCourse.fullname.label("course_name"),
            per.c.period,
            func.sum(case((score >= min_score, 1), else_=0)).label("at_risk_count"),
        )
        .join(totals, totals.c.course_id == per.c.courseid)
        .join(MdlCourse, MdlCourse.id == per.c.courseid)
        .group_by(per.c.courseid, MdlCourse.fullname, per.c.period)
        .order_by(MdlCourse.fullname, per.c.period)
        .all()
    )

    return [
        {
            "course_id": r.course_id,
            "course_name": r.course_name,
            "period": r.period,
            "at_risk_count": int(r.at_risk_count or 0),
        }
        for r in rows
    ]


def get_at_risk_students(
    db: Session,
    min_score: int = RISK_THRESHOLD_DEFAULT,
    course_id: Optional[int] = None,
    period: Optional[str] = None,
    limit: int = 200,
) -> List[Dict[str, Any]]:
    """
    Detalle de entidades en riesgo.
    Si period se provee => por período (user, course, period); si no => all-time (user, course) con last_period.
    """
    if period:
        per = _user_course_period_agg(db)
        score_expr = _risk_score_expr(per.c.failed_count, per.c.absent_count)
        q = (
            db.query(
                per.c.userid.label("user_id"),
                MdlUser.firstname,
                MdlUser.lastname,
                MdlUser.email,
                per.c.courseid.label("course_id"),
                MdlCourse.fullname.label("course_name"),
                per.c.failed_count,
                per.c.absent_count,
                per.c.period.label("last_period"),
            )
            .join(MdlUser, MdlUser.id == per.c.userid)
            .join(MdlCourse, MdlCourse.id == per.c.courseid)
            .filter(score_expr >= min_score)
            .filter(per.c.period == period)
        )
        if course_id:
            q = q.filter(per.c.courseid == course_id)

        rows = (
            q.order_by(
                MdlCourse.fullname.asc(),
                MdlUser.lastname.asc(),
                MdlUser.firstname.asc(),
            )
            .limit(limit)
            .all()
        )

        out: List[Dict[str, Any]] = []
        for r in rows:
            failed = int(r.failed_count or 0)
            absent = int(r.absent_count or 0)
            out.append(
                {
                    "user_id": r.user_id,
                    "firstname": r.firstname,
                    "lastname": r.lastname,
                    "email": r.email,
                    "course_id": r.course_id,
                    "course_name": r.course_name,
                    "failed_count": failed,
                    "absent_count": absent,
                    "last_period": r.last_period,
                    "risk_score": _risk_score(failed, absent),
                    "bucket": _bucket_label(failed, absent),
                }
            )
        return out

    # all-time (sin período)
    agg = _user_course_agg(db)
    score_expr = _risk_score_expr(agg.c.failed_count, agg.c.absent_count)

    q = (
        db.query(
            agg.c.userid.label("user_id"),
            MdlUser.firstname,
            MdlUser.lastname,
            MdlUser.email,
            agg.c.courseid.label("course_id"),
            MdlCourse.fullname.label("course_name"),
            agg.c.failed_count,
            agg.c.absent_count,
            agg.c.last_period,
        )
        .join(MdlUser, MdlUser.id == agg.c.userid)
        .join(MdlCourse, MdlCourse.id == agg.c.courseid)
        .filter(score_expr >= min_score)
    )
    if course_id:
        q = q.filter(agg.c.courseid == course_id)

    rows = (
        q.order_by(
            MdlCourse.fullname.asc(),
            MdlUser.lastname.asc(),
            MdlUser.firstname.asc(),
        )
        .limit(limit)
        .all()
    )

    out: List[Dict[str, Any]] = []
    for r in rows:
        failed = int(r.failed_count or 0)
        absent = int(r.absent_count or 0)
        out.append(
            {
                "user_id": r.user_id,
                "firstname": r.firstname,
                "lastname": r.lastname,
                "email": r.email,
                "course_id": r.course_id,
                "course_name": r.course_name,
                "failed_count": failed,
                "absent_count": absent,
                "last_period": r.last_period,
                "risk_score": _risk_score(failed, absent),
                "bucket": _bucket_label(failed, absent),
            }
        )
    return out


# ===========================
# Helpers de fechas para EXAM DEBT
# ===========================
def _to_unix(date_str: str, end_of_day: bool = False) -> int:
    """Convierte 'YYYY-MM-DD' a UNIX UTC. end_of_day=True => 23:59:59."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    if end_of_day:
        dt = dt + timedelta(days=1) - timedelta(seconds=1)
    return int(dt.replace(tzinfo=timezone.utc).timestamp())


# ===========================
# EXAM DEBT (racha de ausencias) - Base y derivados
# ===========================
def _exam_status_base(db: Session):
    """
    Base: (userid, courseid, ts, is_absent, is_attended)
    ts = timemodified (UNIX) del intento de examen
    Ausente = finalgrade IS NULL
    Asistió (aprobado o reprobado) = finalgrade IS NOT NULL
    """
    return (
        db.query(
            MdlGradeGrades.userid.label("userid"),
            MdlGradeItems.courseid.label("courseid"),
            MdlGradeGrades.timemodified.label("ts"),
            case((MdlGradeGrades.finalgrade.is_(None), 1), else_=0).label("is_absent"),
            case((MdlGradeGrades.finalgrade.isnot(None), 1), else_=0).label("is_attended"),
        )
        .join(MdlGradeItems, MdlGradeGrades.itemid == MdlGradeItems.id)
        .filter(MdlGradeItems.itemtype == "mod")
        .filter(MdlGradeGrades.timemodified.isnot(None))
        .subquery()
    )


def _latest_time_per_pair(db: Session, base):
    """Máximo ts por (user,course)"""
    return (
        db.query(
            base.c.userid.label("userid"),
            base.c.courseid.label("courseid"),
            func.max(base.c.ts).label("last_ts"),
        )
        .group_by(base.c.userid, base.c.courseid)
        .subquery()
    )


def _last_attended_time_per_pair(db: Session, base):
    """Máximo ts asistido por (user,course)"""
    return (
        db.query(
            base.c.userid.label("userid"),
            base.c.courseid.label("courseid"),
            func.max(base.c.ts).label("last_att_ts"),
        )
        .filter(base.c.is_attended == 1)
        .group_by(base.c.userid, base.c.courseid)
        .subquery()
    )


def _absences_after_last_attended(db: Session, base, last_att):
    """
    Cuenta ausencias con ts > last_att_ts (si no hay last_att_ts, usamos 0),
    por (user,course).
    """
    return (
        db.query(
            base.c.userid.label("userid"),
            base.c.courseid.label("courseid"),
            func.count().label("abs_after"),
        )
        .outerjoin(
            last_att,
            and_(
                last_att.c.userid == base.c.userid,
                last_att.c.courseid == base.c.courseid,
            ),
        )
        .filter(base.c.is_absent == 1)
        .filter(base.c.ts > func.coalesce(last_att.c.last_att_ts, 0))
        .group_by(base.c.userid, base.c.courseid)
        .subquery()
    )


def get_exam_debt_rows(
    db: Session,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    months: Optional[List[str]] = None,
    years: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Devuelve filas por (alumno, curso) con:
      user_id, firstname, lastname, email,
      course_id, course_name,
      debt_count (racha de ausencias actuales), last_exam_ts

    Lógica:
      - Si el último examen fue asistido => debt_count=0
      - Si el último fue ausente => debt_count = cantidad de ausencias con ts > last_att_ts
        (si nunca asistió => cuenta todas las ausencias)

    Admite filtros temporales por timemodified:
      - date_from/date_to (YYYY-MM-DD), months=['YYYY-MM'], years=['YYYY']
    """
    # Base con filtros
    base_q = (
        db.query(
            MdlGradeGrades.userid.label("userid"),
            MdlGradeItems.courseid.label("courseid"),
            MdlGradeGrades.timemodified.label("ts"),
            case((MdlGradeGrades.finalgrade.is_(None), 1), else_=0).label("is_absent"),
            case((MdlGradeGrades.finalgrade.isnot(None), 1), else_=0).label("is_attended"),
        )
        .join(MdlGradeItems, MdlGradeGrades.itemid == MdlGradeItems.id)
        .filter(MdlGradeItems.itemtype == "mod")
        .filter(MdlGradeGrades.timemodified.isnot(None))
        .filter(MdlGradeGrades.timemodified <= int(time.time()))
    )
    if date_from:
        base_q = base_q.filter(MdlGradeGrades.timemodified >= _to_unix(date_from))
    if date_to:
        base_q = base_q.filter(MdlGradeGrades.timemodified <= _to_unix(date_to, end_of_day=True))
    if months:
        base_q = base_q.filter(
            func.DATE_FORMAT(func.FROM_UNIXTIME(MdlGradeGrades.timemodified), "%Y-%m").in_(months)
        )
    if years:
        base_q = base_q.filter(
            func.YEAR(func.FROM_UNIXTIME(MdlGradeGrades.timemodified)).in_(
                [int(y) for y in years if str(y).isdigit()]
            )
        )

    base = base_q.subquery()
    latest = _latest_time_per_pair(db, base)
    last_att = _last_attended_time_per_pair(db, base)
    abs_after = _absences_after_last_attended(db, base, last_att)

    # latest row (para saber si el último es ausente)
    latest_row = (
        db.query(
            base.c.userid,
            base.c.courseid,
            base.c.ts.label("last_exam_ts"),
            base.c.is_absent.label("latest_is_absent"),
        )
        .join(
            latest,
            and_(
                latest.c.userid == base.c.userid,
                latest.c.courseid == base.c.courseid,
                latest.c.last_ts == base.c.ts,
            ),
        )
        .subquery()
    )

    # Compose final rows
    rows = (
        db.query(
            latest_row.c.userid.label("user_id"),
            MdlUser.firstname,
            MdlUser.lastname,
            MdlUser.email,
            latest_row.c.courseid.label("course_id"),
            MdlCourse.fullname.label("course_name"),
            latest_row.c.last_exam_ts,
            latest_row.c.latest_is_absent,
            func.coalesce(abs_after.c.abs_after, 0).label("abs_after"),
        )
        .join(MdlUser, MdlUser.id == latest_row.c.userid)
        .join(MdlCourse, MdlCourse.id == latest_row.c.courseid)
        .outerjoin(
            abs_after,
            and_(
                abs_after.c.userid == latest_row.c.userid,
                abs_after.c.courseid == latest_row.c.courseid,
            ),
        )
        .all()
    )

    out: List[Dict[str, Any]] = []
    for r in rows:
        latest_abs = int(r.latest_is_absent or 0)
        abs_after_v = int(r.abs_after or 0)
        debt_count = abs_after_v if latest_abs == 1 else 0
        out.append(
            {
                "user_id": r.user_id,
                "firstname": r.firstname,
                "lastname": r.lastname,
                "email": r.email,
                "course_id": r.course_id,
                "course_name": r.course_name,
                "debt_count": debt_count,
                "last_exam_ts": int(r.last_exam_ts or 0),
            }
        )
    return out


def get_exam_debt_summary(
    db: Session,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    months: Optional[List[str]] = None,
    years: Optional[List[str]] = None,
) -> Dict[str, int]:
    """
    Bucketiza por deuda actual (con los mismos filtros que get_exam_debt_rows):
      - debt_0: al día
      - debt_1: debe 1
      - debt_2: debe 2
      - debt_gt_2: debe +2
    """
    rows = get_exam_debt_rows(db, date_from=date_from, date_to=date_to, months=months, years=years)
    summary = {"debt_0": 0, "debt_1": 0, "debt_2": 0, "debt_gt_2": 0}
    for r in rows:
        d = int(r["debt_count"] or 0)
        if d <= 0:
            summary["debt_0"] += 1
        elif d == 1:
            summary["debt_1"] += 1
        elif d == 2:
            summary["debt_2"] += 1
        else:
            summary["debt_gt_2"] += 1
    return summary


def get_exam_debt_details(
    db: Session,
    bucket: str | int,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    months: Optional[List[str]] = None,
    years: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Filtra por bucket:
      bucket in {"0","1","2","gt2"}  (o ints 0/1/2)
    """
    rows = get_exam_debt_rows(db, date_from=date_from, date_to=date_to, months=months, years=years)
    if bucket in (0, "0"):
        flt = lambda d: d <= 0
    elif bucket in (1, "1"):
        flt = lambda d: d == 1
    elif bucket in (2, "2"):
        flt = lambda d: d == 2
    else:
        flt = lambda d: d >= 3

    out = []
    for r in rows:
        d = int(r["debt_count"] or 0)
        if flt(d):
            out.append(r)
    # ordenamos por curso y apellido
    out.sort(key=lambda x: (x["course_name"] or "", x["lastname"] or "", x["firstname"] or ""))
    return out


# ===========================
# EXAM DEBT (Racha de ausencias) - Agregados por Carrera y Curso
# ===========================
def get_exam_debt_summary_by_course(
    db: Session,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    months: Optional[List[str]] = None,
    years: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Agrega por Carrera (categoría de Moodle) y Curso:
      devuelve: career_id, career_name, course_id, course_name,
                debt_0, debt_1, debt_2, debt_gt_2

    Incluye matriculados (aunque no tengan notas) y aplica filtros temporales
    sobre la "fecha del examen" (quiz): exam_ts = COALESCE(timeclose, timeopen, cm.added),
    recortando a <= NOW().
    """
    params: Dict[str, Any] = {
        "date_from_unix": _to_unix(date_from, end_of_day=False) if date_from else None,
        "date_to_unix": _to_unix(date_to, end_of_day=True) if date_to else None,
    }

    conds: List[str] = ["g.exam_ts <= UNIX_TIMESTAMP()"]
    if params["date_from_unix"] is not None:
        conds.append("g.exam_ts >= :date_from_unix")
    if params["date_to_unix"] is not None:
        conds.append("g.exam_ts <= :date_to_unix")
    if months:
        conds.append("DATE_FORMAT(FROM_UNIXTIME(g.exam_ts),'%Y-%m') IN :months")
        params["months"] = months
    if years:
        conds.append("YEAR(FROM_UNIXTIME(g.exam_ts)) IN :years")
        params["years"] = [int(y) for y in years if str(y).isdigit()]

    where_clause = ""
    if conds:
        where_clause = "WHERE " + " AND ".join(conds)

    sql_str = f"""
        WITH enrolled AS (
            SELECT ue.userid AS user_id, e.courseid AS course_id
            FROM mdl_user_enrolments ue
            JOIN mdl_enrol e ON e.id = ue.enrolid
            WHERE ue.status = 0 AND e.status = 0
        ),
        gi_cm AS (
            SELECT
                gi.id           AS gi_id,
                gi.courseid     AS course_id,
                gi.itemmodule   AS itemmodule,
                gi.iteminstance AS iteminstance,
                cm.id           AS cmid,
                cm.section      AS section_id,
                cs.name         AS section_name,
                cs.section      AS section_num,
                CASE
                  WHEN gi.itemmodule = 'quiz' THEN
                    COALESCE(NULLIF(q.timeclose,0), NULLIF(q.timeopen,0), cm.added)
                  ELSE
                    cm.added
                END AS exam_ts
            FROM mdl_grade_items gi
            JOIN mdl_modules m
              ON m.name = gi.itemmodule
            JOIN mdl_course_modules cm
              ON cm.module = m.id
             AND cm.instance = gi.iteminstance
             AND cm.course = gi.courseid
            LEFT JOIN mdl_course_sections cs
              ON cs.id = cm.section
            LEFT JOIN mdl_quiz q
              ON q.id = gi.iteminstance
             AND gi.itemmodule = 'quiz'
            WHERE gi.itemtype = 'mod'
              AND gi.itemmodule = 'quiz'
        ),
        ordered AS (
            SELECT
                en.user_id,
                g.course_id,
                g.gi_id,
                g.exam_ts,
                CASE WHEN gg.finalgrade IS NULL THEN 1 ELSE 0 END AS is_absent,
                ROW_NUMBER() OVER (
                  PARTITION BY en.user_id, g.course_id
                  ORDER BY g.exam_ts DESC, g.gi_id DESC
                ) AS rn,
                SUM(
                  CASE WHEN gg.finalgrade IS NULL THEN 0 ELSE 1 END
                ) OVER (
                  PARTITION BY en.user_id, g.course_id
                  ORDER BY g.exam_ts DESC, g.gi_id DESC
                  ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) AS seen_present
            FROM enrolled en
            JOIN gi_cm g
              ON g.course_id = en.course_id
            LEFT JOIN mdl_grade_grades gg
              ON gg.itemid = g.gi_id
             AND gg.userid = en.user_id
            {where_clause}
        ),
        streak AS (
            SELECT
                o.user_id,
                o.course_id,
                COALESCE(SUM(CASE WHEN o.is_absent = 1 AND o.seen_present = 0 THEN 1 ELSE 0 END), 0) AS debt_count
            FROM ordered o
            GROUP BY o.user_id, o.course_id
        )
        SELECT
            c.category                         AS career_id,
            COALESCE(cc.name, 'Sin categoría') AS career_name,
            c.id                               AS course_id,
            c.fullname                         AS course_name,
            SUM(CASE WHEN s.debt_count <= 0 THEN 1 ELSE 0 END) AS debt_0,
            SUM(CASE WHEN s.debt_count = 1 THEN 1 ELSE 0 END)  AS debt_1,
            SUM(CASE WHEN s.debt_count = 2 THEN 1 ELSE 0 END)  AS debt_2,
            SUM(CASE WHEN s.debt_count >= 3 THEN 1 ELSE 0 END) AS debt_gt_2
        FROM streak s
        JOIN mdl_course c
          ON c.id = s.course_id
        LEFT JOIN mdl_course_categories cc
          ON cc.id = c.category
        GROUP BY c.category, cc.name, c.id, c.fullname
        ORDER BY cc.name ASC, c.fullname ASC
    """
    sql = text(sql_str)
    if months:
        sql = sql.bindparams(bindparam("months", expanding=True))
    if years:
        sql = sql.bindparams(bindparam("years", expanding=True))

    rows = db.execute(sql, params).mappings().all()

    result: List[Dict[str, Any]] = []
    for r in rows:
        result.append({
            "career_id": r["career_id"] if r["career_id"] is not None else 0,
            "career_name": r["career_name"] or "Sin categoría",
            "course_id": r["course_id"],
            "course_name": r["course_name"],
            "debt_0": int(r["debt_0"] or 0),
            "debt_1": int(r["debt_1"] or 0),
            "debt_2": int(r["debt_2"] or 0),
            "debt_gt_2": int(r["debt_gt_2"] or 0),
        })
    return result


def get_exam_debt_summary_by_section(db: Session, course_id: int) -> List[Dict[str, Any]]:
    """
    Calcula la 'deuda de exámenes' por SECCIÓN dentro de un curso.
    Mantiene tu definición actual (sin filtros temporales).
    """
    sql = text("""
        WITH gi_cm AS (
            SELECT
                gi.id              AS gi_id,
                gi.courseid        AS course_id,
                gi.itemmodule      AS itemmodule,
                gi.iteminstance    AS iteminstance,
                gi.gradepass       AS gradepass,
                cm.id              AS cmid,
                cm.section         AS section_id,
                cs.name            AS section_name,
                cs.section         AS section_num,
                cm.added           AS exam_ts
            FROM mdl_grade_items gi
            JOIN mdl_modules m
              ON m.name = gi.itemmodule
            JOIN mdl_course_modules cm
              ON cm.module = m.id
             AND cm.instance = gi.iteminstance
             AND cm.course = gi.courseid
            JOIN mdl_course_sections cs
              ON cs.id = cm.section
            WHERE gi.itemtype = 'mod'
              AND gi.courseid = :course_id
        ),
        ordered AS (
            SELECT
                gg.userid                  AS user_id,
                g.gi_id,
                g.course_id,
                g.section_id,
                COALESCE(g.section_name, CONCAT('Sección ', g.section_num)) AS section_name,
                g.gradepass,
                gg.finalgrade,
                g.exam_ts,
                ROW_NUMBER() OVER (PARTITION BY gg.userid ORDER BY g.exam_ts DESC, g.gi_id DESC) AS rn,
                CASE
                  WHEN gg.finalgrade IS NULL THEN 1
                  WHEN (g.gradepass IS NULL OR g.gradepass = 0) THEN 0
                  WHEN gg.finalgrade < g.gradepass THEN 1
                  ELSE 0
                END AS is_absent,
                SUM(
                  CASE
                    WHEN gg.finalgrade IS NULL THEN 0
                    WHEN (g.gradepass IS NULL OR g.gradepass = 0) THEN 1
                    WHEN gg.finalgrade >= g.gradepass THEN 1
                    ELSE 0
                  END
                ) OVER (
                  PARTITION BY gg.userid
                  ORDER BY g.exam_ts DESC, g.gi_id DESC
                  ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) AS seen_present
            FROM gi_cm g
            LEFT JOIN mdl_grade_grades gg
              ON gg.itemid = g.gi_id
            WHERE g.course_id = :course_id
        ),
        streak AS (
            SELECT
                o.user_id,
                SUM(o.is_absent) AS consec_absences
            FROM ordered o
            WHERE o.seen_present = 0
            GROUP BY o.user_id
        ),
        latest AS (
            SELECT
                o.user_id,
                o.section_id,
                o.section_name
            FROM ordered o
            WHERE o.rn = 1
        )
        SELECT
            l.section_id,
            l.section_name,
            SUM(CASE WHEN s.consec_absences = 0 THEN 1 ELSE 0 END) AS debt_0,
            SUM(CASE WHEN s.consec_absences = 1 THEN 1 ELSE 0 END) AS debt_1,
            SUM(CASE WHEN s.consec_absences = 2 THEN 1 ELSE 0 END) AS debt_2,
            SUM(CASE WHEN s.consec_absences >= 3 THEN 1 ELSE 0 END) AS debt_gt_2
        FROM latest l
        JOIN streak s
          ON s.user_id = l.user_id
        GROUP BY l.section_id, l.section_name
        ORDER BY l.section_name ASC
    """)
    rows = db.execute(sql, {"course_id": course_id}).mappings().all()
    return [dict(r) for r in rows]