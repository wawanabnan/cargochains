from typing import Optional
from core.models import CompanyInformation


def get_company() -> Optional[CompanyInformation]:
    return CompanyInformation.objects.first()
