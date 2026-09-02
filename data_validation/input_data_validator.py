import json
import re
import starlette.status as status
from error_codes.auth_error_code import AuthErrorCode


EMAIL_REGEX = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$")


def _get_validation_response(code:str,message:str,is_error:bool=True,status_code:int=status.HTTP_400_BAD_REQUEST,data=None) -> dict:
    return {"is_error":is_error,"status_code":status_code,"response":{"code":code,"message":message,"data":data}}


def validate_auth_input(body,required_fields:list,is_login:bool=False)-> dict[str, bool | dict[str, str | None]] | None:
    try:
        dict_body = json.loads(body)
    except json.decoder.JSONDecodeError:
        return _get_validation_response(AuthErrorCode.AU101.name,AuthErrorCode.AU101.value)

    if dict_body:
        try:
            for field in required_fields: #checks for the required fields
                if field not in dict_body:
                    return _get_validation_response(AuthErrorCode.AU102.name, AuthErrorCode.AU102.value)

                if dict_body[field] is None or dict_body[field] == "": #check for empty fields
                    if field in ("email", "email_id"):
                        return _get_validation_response(AuthErrorCode.AU103.name, AuthErrorCode.AU103.value)
                    if field == "phone":
                        return _get_validation_response(AuthErrorCode.AU104.name, AuthErrorCode.AU104.value)
                    if field == "username":
                        return _get_validation_response(AuthErrorCode.AU110.name, AuthErrorCode.AU110.value)
                    if field == "role":
                        return _get_validation_response(AuthErrorCode.AU105.name, AuthErrorCode.AU105.value)
                    if field == "password":
                        return _get_validation_response(AuthErrorCode.AU106.name, AuthErrorCode.AU106.value)
                    if field == "data":
                        return _get_validation_response(AuthErrorCode.AU116.name, AuthErrorCode.AU116.value)
                if not is_login:
                    if field == "email":
                        email_validation_response = __validate_email(dict_body[field])
                        if email_validation_response:
                            return email_validation_response
                    if field == "password":
                        password_validation_response = __validate_password(dict_body[field])
                        if password_validation_response:
                            return password_validation_response

            return _get_validation_response(AuthErrorCode.AU109.name, AuthErrorCode.AU109.value,is_error=False,status_code=status.HTTP_200_OK,data=dict_body)

        except Exception as e:
            return _get_validation_response(AuthErrorCode.AU107.name, AuthErrorCode.AU107.value,status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return _get_validation_response(AuthErrorCode.AU108.name, AuthErrorCode.AU108.value,status_code=status.HTTP_400_BAD_REQUEST)


def __validate_email(email:str)-> dict[str, bool | dict[str, str | None]] | None:
    try:
        if not isinstance(email, str):
            return _get_validation_response(AuthErrorCode.AU111.name, AuthErrorCode.AU111.value)

        email = email.strip()
        if (
            len(email) > 254
            or not EMAIL_REGEX.fullmatch(email)
            or ".." in email
            or email.startswith(".")
            or email.endswith(".")
        ):
            return _get_validation_response(AuthErrorCode.AU111.name, AuthErrorCode.AU111.value)

        local_part, domain = email.rsplit("@", 1)
        if len(local_part) > 64 or any(len(label) > 63 for label in domain.split(".")):
            return _get_validation_response(AuthErrorCode.AU111.name, AuthErrorCode.AU111.value)

        return None
    except Exception:
        return _get_validation_response(
            AuthErrorCode.AU107.name,
            AuthErrorCode.AU107.value,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


def __validate_password(password:str)-> dict[str, bool | dict[str, str | None]] | None:
    try:
        if not isinstance(password, str):
            return _get_validation_response(AuthErrorCode.AU112.name, AuthErrorCode.AU112.value)

        if (
            len(password) < 8
            or len(password) > 64
            or any(character.isspace() for character in password)
            or not re.search(r"[a-z]", password)
            or not re.search(r"[A-Z]", password)
            or not re.search(r"\d", password)
            or not re.search(r"[^A-Za-z0-9]", password)
        ):
            return _get_validation_response(AuthErrorCode.AU112.name, AuthErrorCode.AU112.value)

        return None
    except Exception:
        return _get_validation_response(
            AuthErrorCode.AU107.name,
            AuthErrorCode.AU107.value,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

