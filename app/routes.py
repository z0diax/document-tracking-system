import json

from app.route_modules import admin_dashboard as _admin_dashboard_routes  
from app.route_modules import admin_missing_offices as _admin_missing_office_routes  
from app.route_modules import admin_sla as _admin_sla_routes  
from app.route_modules import admin_user_access as _admin_user_access_routes  
from app.route_modules import admin_user_lifecycle as _admin_user_lifecycle_routes  
from app.route_modules import auth as _auth_routes  
from app.route_modules import dashboard as _dashboard_routes  
from app.route_modules import document_actions as _document_action_routes  
from app.route_modules import employees as _employee_routes  
from app.route_modules import leave as _leave_routes  
from app.route_modules import misc_pages as _misc_page_routes  
from app.route_modules import release_api as _release_api  
from app.route_modules import reporting as _reporting_routes  
from app.route_modules import rsp as _rsp_routes  
from app.route_modules.shared import main


@main.app_template_filter('escapejs')
def escapejs_filter(value):
    return json.dumps(value)[1:-1]
