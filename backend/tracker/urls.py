from django.urls import path

from . import views

urlpatterns = [
    # public
    path("config/", views.ConfigView.as_view()),
    path("register/", views.RegisterView.as_view()),
    path("webhook/sms/", views.WebhookView.as_view()),
    # sign in
    path("auth/login/", views.LoginView.as_view()),
    path("auth/me/", views.MeView.as_view()),
    path("auth/logout/", views.LogoutView.as_view()),
    # treasurer / admin
    path("dashboard/", views.DashboardView.as_view()),
    path("members/", views.MemberListView.as_view()),
    path("members/<int:pk>/", views.MemberDetailView.as_view()),
    path("payments/", views.PaymentListView.as_view()),
    path("payments/<int:pk>/assign/", views.PaymentAssignView.as_view()),
    path("payments/<int:pk>/reverse/", views.PaymentReverseView.as_view()),
    path("payments/<int:pk>/resend/", views.PaymentResendView.as_view()),
    path("incoming/", views.IncomingListView.as_view()),
    path("export/", views.ExportView.as_view()),
]
