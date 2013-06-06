def string_attr(the_object, the_attribute):
    prop = getattr(the_object, the_attribute, None)
    if prop:
        try:
            return str(prop)
        except:
            return None
    else:
        return None
