from fastapi.routing import APIRouter

from app.application.api.v1.ai.handlers import router as ai_router
from app.application.api.v1.gamification.handlers import router as gamification_router
from app.application.api.v1.likes.handlers import router as likes_router
from app.application.api.v1.payments.handlers import router as payments_router
from app.application.api.v1.photo_interactions.handlers import router as photo_interactions_router
from app.application.api.v1.profile_questions.handlers import router as profile_questions_router
from app.application.api.v1.users.handlers import router as users_router
from app.application.api.v1.webhooks.telegram import router as telegram_webhook_router


router = APIRouter(
    prefix="/v1",
)

router.include_router(users_router)
router.include_router(likes_router)
router.include_router(telegram_webhook_router)
router.include_router(ai_router)
router.include_router(gamification_router)
router.include_router(payments_router)
router.include_router(photo_interactions_router)
router.include_router(profile_questions_router)
