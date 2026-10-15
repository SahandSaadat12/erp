from ..common.delete import delete_record

from .refresh_projects import refresh_projects


def delete_project(database, tree):

    delete_record(
        database=database,
        tree=tree,
        table_name="projects",
        get_record=database.get_project_by_code,
        refresh_function=refresh_projects,
        record_name="project",
        cascade=True
    )