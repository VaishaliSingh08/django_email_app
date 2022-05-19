from django.contrib import admin
from django.urls import path, include
from mailSystem import  views


urlpatterns = [
    path('', views.login, name='login'),
    path('compose_mail', views.compose_mail, name='compose_mail'),
    # path('reply_mail', views.reply_mail, name='reply_mail'),
    path('login', views.login, name='login'),
    path('logout', views.logout, name='logout'),
    path('mail/<str:slug>', views.mail, name='mail'),
    path('move_mails', views.move_mails, name='move_mails'),
    path('move_label_mails', views.move_label_mails, name='move_label_mails'),
    path('star_mail', views.star_mail, name='star_mail'),
    path('delete_spam_mail', views.delete_spam_mail, name='delete_spam_mail'),
    path('get_attachment_path/<str:slug>', views.get_attachment_path, name='get_attachment_path'),
    path('set_msg_as_draft', views.set_msg_as_draft, name='set_msg_as_draft'),
    path('mark_mail_as_read', views.mark_mail_as_read, name='mark_mail_as_read'),


]


