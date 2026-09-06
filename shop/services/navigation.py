"""Build the active category tree once per request, without recursive SQL queries."""
from shop.models import Category


def navigation_tree():
    nodes = list(Category.objects.filter(is_active=True).order_by('order', 'name'))
    by_id = {node.pk: node for node in nodes}
    roots = []
    for node in nodes:
        node.menu_children = []
    for node in nodes:
        if node.parent_id is None:
            roots.append(node)
        elif node.parent_id in by_id:
            by_id[node.parent_id].menu_children.append(node)
    return roots


def descendant_ids(category):
    pairs = list(Category.objects.filter(is_active=True).values_list('id', 'parent_id'))
    selected = {category.pk}
    while True:
        children = {pk for pk, parent in pairs if parent in selected} - selected
        if not children:
            return selected
        selected.update(children)
