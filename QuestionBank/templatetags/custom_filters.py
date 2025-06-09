# custom_filters.py
from django import template

register = template.Library()

@register.filter
def split_lines(value):
    return value.split('\n')

from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)
