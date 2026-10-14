from fastapi import APIRouter

from app.api.routes import admin, advisories, alerts, applications, assistant, auth, clusters, onboarding, phc, profile, registry, schedule, settings, vitals

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(onboarding.router)
api_router.include_router(vitals.router)
api_router.include_router(alerts.router)
api_router.include_router(advisories.router)
api_router.include_router(clusters.router)
api_router.include_router(alerts.phc_router)
api_router.include_router(schedule.router)
api_router.include_router(phc.router)
api_router.include_router(settings.router)
api_router.include_router(profile.router)
api_router.include_router(admin.router)
api_router.include_router(applications.router)
api_router.include_router(applications.admin_router)
api_router.include_router(registry.router)
api_router.include_router(assistant.router)
