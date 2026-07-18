from django import template

register = template.Library()


@register.filter
def get_item(dictionnaire, cle):
    """Lit une valeur de dict par clé variable : {{ mon_dict|get_item:ma_cle }}"""
    if not dictionnaire:
        return None
    return dictionnaire.get(cle)


@register.filter
def field(form, name):
    """Récupère un champ du formulaire par son nom : {{ form|field:'ncc' }}"""
    try:
        return form[name]
    except KeyError:
        return None