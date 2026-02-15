class EmailNotValidError(ValueError):
    pass


class ValidatedEmail:
    def __init__(self, email: str):
        self.email = email



def validate_email(email: str, *args, **kwargs):
    if '@' not in email:
        raise EmailNotValidError('Invalid email address')
    return ValidatedEmail(email)
