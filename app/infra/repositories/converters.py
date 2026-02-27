from typing import (
    Any,
    Mapping,
)

from app.domain.entities.likes import LikesEntity
from app.domain.entities.users import UserEntity


def convert_user_entity_to_document(user: UserEntity) -> dict:
    return {
        "telegram_id": user.telegram_id,
        "username": user.username,
        "name": user.name.as_generic_type() if user.name else None,
        "gender": user.gender.as_generic_type() if user.gender else None,
        "age": user.age.as_generic_type() if user.age else None,
        "city": user.city.as_generic_type() if user.city else None,
        "looking_for": user.looking_for.as_generic_type() if user.looking_for else None,
        "about": user.about.as_generic_type() if user.about else None,
        "photo": user.photo if user.photo else None,
        "photos": user.photos if user.photos else [],
        "is_active": user.is_active,
        "profile_hidden": user.profile_hidden,
        "premium_type": user.premium_type,
        "premium_until": user.premium_until,
        "superlike_credits": user.superlike_credits or 0,
        "boost_until": user.boost_until,
        "boosts_this_week": user.boosts_this_week or 0,
        "boost_week_reset": user.boost_week_reset,
        "referred_by": user.referred_by,
        "referral_balance": user.referral_balance or 0.0,
        "last_seen": user.last_seen,
        "profile_answers": user.profile_answers or {},
        "created_at": user.created_at,
    }


def convert_user_document_to_entity(user_document: Mapping[str, Any]) -> UserEntity:
    return UserEntity(
        telegram_id=int(user_document["telegram_id"]),
        username=user_document["username"],
        name=user_document["name"] if user_document["name"] else None,
        gender=user_document["gender"] if user_document["gender"] else None,
        age=user_document["age"] if user_document["age"] else None,
        city=user_document["city"] if user_document["city"] else None,
        looking_for=user_document["looking_for"]
        if user_document["looking_for"]
        else None,
        about=user_document["about"] if user_document["about"] else None,
        photo=user_document["photo"] if user_document.get("photo") else None,
        photos=user_document.get("photos") or [],
        is_active=user_document.get("is_active", True),
        profile_hidden=bool(user_document.get("profile_hidden", False)),
        premium_type=user_document.get("premium_type"),
        premium_until=user_document.get("premium_until"),
        superlike_credits=int(user_document.get("superlike_credits") or 0),
        boost_until=user_document.get("boost_until"),
        boosts_this_week=int(user_document.get("boosts_this_week") or 0),
        boost_week_reset=user_document.get("boost_week_reset"),
        referred_by=user_document.get("referred_by"),
        referral_balance=float(user_document.get("referral_balance") or 0.0),
        last_seen=user_document.get("last_seen"),
        profile_answers=user_document.get("profile_answers"),
        created_at=user_document["created_at"],
    )


def convert_like_entity_to_document(like: LikesEntity) -> dict:
    return {
        "from_user": like.from_user.as_generic_type(),
        "to_user": like.to_user.as_generic_type(),
        "created_at": like.created_at,
    }
