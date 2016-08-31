
class SSRouter(object):

    def db_for_read(self, model, **hints):
#        if model._meta.app_label == 'auth':
#            return 'auth_db'
        return 'ss'

    def db_for_write(self, model, **hints):
        return 'ss'

    def allow_relation(self, obj1, obj2, **hints):
        return 'ss'

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return db == 'ss'

