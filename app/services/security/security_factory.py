from settings.config import (
    KEYCLOAK_AUTHORIZATION_URL,
    KEYCLOAK_PUBLIC_KEY_URL,
    KEYCLOAK_TOKEN_URL,
    SECURITY_MIDDLEWARE_URL,
    SECURITY_TYPE,
)

from services.security.implementation.disabled import DisabledSecurity
from services.security.implementation.keycloak import Keycloak, KeycloakInfo
from services.security.implementation.utils.user_info_cache import (
    UserInfoCache,
)
from services.security.security_interface import SecurityInterface


class SecurityFactory:
    def get(self, security_type: str) -> SecurityInterface:
        match security_type.upper():
            case "KEYCLOAK":
                return self._get_keycloak()
            case "KEYCLOAK-INFO":
                return self._get_keycloak_info()
            case _:
                return self._get_disabled()

    @staticmethod
    def _get_disabled() -> SecurityInterface:
        return DisabledSecurity()

    def _get_keycloak(self) -> SecurityInterface:
        keycloak_public_url = KEYCLOAK_PUBLIC_KEY_URL
        token_url = KEYCLOAK_TOKEN_URL
        authorization_url = KEYCLOAK_AUTHORIZATION_URL
        refresh_url = authorization_url
        scopes = {
            "profile": "Read claims that represent basic profile information"
        }

        return Keycloak(
            keycloak_public_url=keycloak_public_url,
            token_url=token_url,
            authorization_url=authorization_url,
            refresh_url=refresh_url,
            scopes=scopes,
        )

    def _get_keycloak_info(self) -> SecurityInterface:
        keycloak_public_url = KEYCLOAK_PUBLIC_KEY_URL
        token_url = KEYCLOAK_TOKEN_URL
        authorization_url = KEYCLOAK_AUTHORIZATION_URL
        refresh_url = authorization_url
        scopes = {
            "profile": "Read claims that represent basic profile information"
        }
        cache = UserInfoCache()
        cache_user_info_url = SECURITY_MIDDLEWARE_URL
        return KeycloakInfo(
            cache=cache,
            keycloak_public_url=keycloak_public_url,
            token_url=token_url,
            authorization_url=authorization_url,
            refresh_url=refresh_url,
            scopes=scopes,
            cache_user_info_url=cache_user_info_url,
        )


print("Set Security Type to", SECURITY_TYPE)
security = SecurityFactory().get(SECURITY_TYPE)
