from django.template import Library
from django.core.urlresolvers import reverse, NoReverseMatch
from django.utils.encoding import smart_text
from django.utils.safestring import mark_safe
from django.contrib.admin.utils import lookup_field
from django.core.exceptions import ObjectDoesNotExist

from ..utils import get_admin_url, GenericObjects


register = Library()


@register.filter
def contents_or_fk_link(field):
    """
    Return field contents or link to related object if foreign key field

    Example Usage::

        {% load relatives %}
        {{ field|contents_or_fk_link }}
    """
    contents = field.contents()
    field_name = field.field['field']
    obj = field.form.instance
    try:
        related_obj = getattr(obj, field_name)
    except ObjectDoesNotExist:
        return contents
    else:
        model_field, _, _ = lookup_field(field_name, obj, field.model_admin)[0]
        if getattr(model_field, 'rel') and hasattr(related_obj, '_meta'):
            try:
                return mark_safe('<a href="%s">%s</a>' %
                                 (get_admin_url(related_obj), contents))
            except NoReverseMatch:
                pass
        return contents


@register.assignment_tag
def related_objects(obj):
    """
    Return list of objects related to the given model instance

    Example Usage::

        {% load relatives %}
        {% related_objects obj as related_objects %}
        {% for related_obj in related_objects %}
            <a href="{{ related_obj.url }}">{{ related_obj.plural_name }}</a>
        {% endfor %}
    """
    object_list = []
    all_related_objects = [
        f for f in obj._meta.get_fields()
        if (f.one_to_many or f.one_to_one)
        and f.auto_created and not f.concrete
    ]
    all_related_m2m_objects = [
        f for f in obj._meta.get_fields(include_hidden=True)
        if f.many_to_many and f.auto_created
    ]
    related_objects = (all_related_objects +
                       all_related_m2m_objects +
                       GenericObjects(obj).get_generic_objects())
    for related in related_objects:
        try:
            to_model = getattr(related, 'related_model', related.model)
            url = reverse('admin:{0}_{1}_changelist'.format(
                to_model._meta.app_label,
                to_model._meta.model_name
            ))
        except NoReverseMatch:
            continue
        object_list.append({
            'plural_name': to_model._meta.verbose_name_plural,
            'url': smart_text('%s?%s=%s' % (url, related.field.name, obj.pk)),
        })
    return object_list
