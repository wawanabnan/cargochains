from accounting.models.journal import JournalLine


def account_is_used(account) -> bool:
    """
    Return True jika account sudah dipakai di journal line manapun.
    """
    return JournalLine.objects.filter(account=account).exists()
