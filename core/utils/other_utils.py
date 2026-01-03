def get_valid_days_default():
    try:
        rec = CoreSetting.objects.get(key=" quotation_valid_days")
        return int(rec.value)
    except:
        return 7  