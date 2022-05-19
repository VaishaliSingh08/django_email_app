from mailSystem.models import User
from django.db.models import Q


def check_user_exist(email, password):
    object_values = User.objects.filter(email=email, password=password)
    return object_values

def get_id(table_name, email):
    object_values = table_name.objects.filter(user_email=email).values()
    object_values = list(object_values)
    return object_values

def get_all_object_from_id(table_name,key):
    object_values = table_name.objects.filter(pk=key).values()
    object_values = list(object_values)
    return object_values


def get_detials_from_id_with_user_id(tablename, id, field_name, uid):
    # # print(id)
    # id = id.split(',')

    kwargs = {
        '{0}'.format(field_name): id
    }
    # # print(kwargs)
    object_values = tablename.objects.filter(Q(**kwargs), Q(user_id_fk=uid)).values()
    # object_values = list(object_values)
    # # print(object_values)
    return object_values
