from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand
from info import create_app, db, models
from config import DevelopmentConfig, ProductionConfig
import logging

app = create_app(DevelopmentConfig)

# start manage commond
manager = Manager(app)
# register project and database to migration
Migrate(app, db)
# add command to manager and we will to use command python manage runserver in the terminal
manager.add_command('db', MigrateCommand)

if __name__ == '__main__':
    # the manager running
    logging.info(app.url_map)
    manager.run()
