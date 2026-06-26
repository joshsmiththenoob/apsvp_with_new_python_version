from django.urls import path
from . import views
urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('chart/', views.ChartPageView.as_view(), name='chart_page'),
    path('hello_world/', views.hello_world, name='hello_world'),
]
