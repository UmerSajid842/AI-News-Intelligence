from pydantic import BaseModel


class Settings(BaseModel):
    authjwt_secret_key: str = "super-secret-key-change-me-in-production"
    authjwt_token_location: set = {"headers"}
    authjwt_header_name: str = "Authorization"
    authjwt_header_type: str = "Bearer"
