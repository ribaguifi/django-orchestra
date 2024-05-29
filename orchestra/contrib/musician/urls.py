
"""
URL routes definition.

Describe the paths where the views are accesible.
"""
from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = 'musician'

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='musician:dashboard', permanent=False), name='index'),

    path('auth/login/', views.LoginView.as_view(), name='login'),
    path('auth/logout/', views.LogoutView.as_view(), name='logout'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),

    path('domains/<int:pk>/', views.DomainDetailView.as_view(), name='domain-detail'),
    path('domains/<int:pk>/add-record/', views.DomainAddRecordView.as_view(), name='domain-add-record'),
    path('domains/<int:pk>/records/<int:record_pk>/update/', views.DomainUpdateRecordView.as_view(), name='domain-update-record'),
    path('domains/<int:pk>/records/<int:record_pk>/delete/', views.DomainDeleteRecordView.as_view(), name='domain-delete-record'),

    path('billing/', views.BillingView.as_view(), name='billing'),
    path('bills/<int:pk>/download/', views.BillDownloadView.as_view(), name='bill-download'),
    
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('profile/setLang/<code>', views.profile_set_language, name='profile-set-lang'),
    
    path('address/', views.AddressListView.as_view(), name='address-list'),
    path('address/new/', views.MailCreateView.as_view(), name='address-create'),
    path('address/<int:pk>/', views.MailUpdateView.as_view(), name='address-update'),
    path('address/<int:pk>/delete/', views.AddressDeleteView.as_view(), name='address-delete'),
    
    path('mailboxes/', views.MailboxListView.as_view(), name='mailbox-list'),
    path('mailboxes/new/', views.MailboxCreateView.as_view(), name='mailbox-create'),
    path('mailboxes/<int:pk>/', views.MailboxUpdateView.as_view(), name='mailbox-update'),
    path('mailboxes/<int:pk>/delete/', views.MailboxDeleteView.as_view(), name='mailbox-delete'),
    path('mailboxes/<int:pk>/change-password/', views.MailboxChangePasswordView.as_view(), name='mailbox-password'),
    
    path('mailing-lists/', views.MailingListsView.as_view(), name='mailing-lists'),
    
    path('databases/', views.DatabaseListView.as_view(), name='database-list'),
    
    path('saas/', views.SaasListView.as_view(), name='saas-list'),
    
    path('webappusers/', views.WebappUserListView.as_view(), name='webappuser-list'),
    path('webappuser/<int:pk>/change-password/', views.WebappUserChangePasswordView.as_view(), name='webappuser-password'),
    path('systemusers/', views.SystemUserListView.as_view(), name='systemuser-list'),
    path('systemuser/<int:pk>/change-password/', views.SystemUserChangePasswordView.as_view(), name='systemuser-password'),
    
    path('websites/', views.WebsiteListView.as_view(), name='website-list'),
    path('websites/<int:pk>/', views.WebsiteDetailView.as_view(), name='website-detail'),
    path('websites/<int:pk>/edit/', views.WebsiteUpdateView.as_view(), name='website-update'),
    path('websites/<int:pk>/add-content/', views.WebsiteAddContentView.as_view(), name='website-add-content'),
    path('websites/<int:pk>/add-directive/', views.WebsiteAddDirectiveView.as_view(), name='website-add-directive'),
    path('websites/<int:pk>/content/<int:content_pk>/delete/', views.WebsiteDeleteContentView.as_view(), name='website-delete-content'),
    path('websites/<int:pk>/directive/<int:directive_pk>/delete/', views.WebsiteDeleteDirectiveView.as_view(), name='website-delete-directive'),

    path('webapps/', views.WebappListView.as_view(), name='webapp-list'),
    path('webapps/<int:pk>/', views.WebappDetailView.as_view(), name='webapp-detail'),
    path('webapps/<int:pk>/add-option/', views.WebappAddOptionView.as_view(), name='webapp-add-option'),
    path('webapps/<int:pk>/option/<int:option_pk>/delete/', views.WebappDeleteOptionView.as_view(), name='webapp-delete-option'),
    path('webapps/<int:pk>/option/<int:option_pk>/update/', views.WebappUpdateOptionView.as_view(), name='webapp-update-option'),
]
