from core.models.setup  import SetupState


def get_setup_state() -> SetupState:
    obj = SetupState.objects.first()
    if not obj:
        obj = SetupState.objects.create(is_completed=False, current_step=1)
    return obj
