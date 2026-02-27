def is_finance(user):
    return user.is_authenticated and (user.is_superuser or user.groups.filter(name="finances").exists())
