from django.urls import path
from django.conf.urls.static import static
from django.conf import settings
from . import views

app_name = 'djangoapp'
urlpatterns = [
    # route is a string contains a URL pattern
    # view refers to the view function
    # name the URL
    path(route='login', view=views.login_user, name='login'),
    path(route='logout', view=views.logout_request, name='logout'),
    path(route='register', view=views.registration, name='register'),
    
    # Add the get_cars path right here:
    path(route='get_cars', view=views.get_cars, name='getcars'),

    # ... your other paths ...
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)