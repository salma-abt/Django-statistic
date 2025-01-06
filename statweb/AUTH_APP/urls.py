from django.urls import path 
from .views import  *

urlpatterns = [
    path('', upload_excel, name="home"),
    path('sign_up/', sign_up, name="sign_up"),
    path('logout/',logoutUser,name='logout'),
    path('login/',CustomLoginView.as_view(),name='login'),
    path('upload/', upload_excel, name='upload_excel'),
    path('user_files/', user_files, name='user_files'),
    path('delete_file/<int:file_id>/', delete_file, name='delete_file'),
    path('view_file/<int:file_id>/', view_file, name='view_file'),
    path('index_file/<int:file_id>/', index_file, name='index_file'),
    path('slice_file/<int:file_id>/', slice_file, name='slice_file'),
    path('vis_file/<int:file_id>/', vis_file, name='vis_file'),
    path('prob_file/<int:file_id>/', prob_file, name='prob_file'),
]