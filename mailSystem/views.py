import json
import os
import time
from binascii import hexlify
from os.path import basename
from email import encoders

from django.contrib.sites.shortcuts import get_current_site
from django.core.files.storage import FileSystemStorage
from proj1.settings import emails_count, MEDIA_URL, MEDIA_ROOT
from django.urls import reverse
import html2text as html2text
from django.shortcuts import render, redirect
from django.http import HttpResponse
from proj1 import database_functions as db
from mailSystem.models import User, SentMails
import imaplib
from mailSystem import utilities as utl
import pprint
import datetime
import email
import smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.base import MIMEBase
import re


# Create your views here.
### Method for home page

def login(request):
    if request.method == 'POST':
        username = request.POST['username']
        user_email = request.POST['user_email']
        password = request.POST['password']
        encoded_pass = utl.my_encrypt(utl.key, bytes(password, 'utf-8'))
        encrypted_pass = encoded_pass.decode()
        host = request.POST['host']

        if host == "gmail":
            user_exist = User.objects.filter(user_email=user_email)
            if user_exist:
                u = User.objects.filter(user_email=user_email).update(user_pass=encrypted_pass, user_name=username)
            else:
                u = User.objects.create(user_name=username, user_email=user_email, in_server='imap.gmail.com',
                                        user_pass=encrypted_pass, user_host='gmail', in_port=993,
                                        out_server='smtp.gmail.com', out_port=465)
                u.save()
            request.session['user_email'] = user_email
            uid = db.get_id(User, user_email)
            request.session['user_id'] = uid[0]['user_id']
            request.session['user_pass'] = password
            request.session['host'] = host
            utl.get_gmail_labels(request)

            return redirect('mail/inbox')

        elif host == "outlook":
            user_exist = User.objects.filter(user_email=user_email)
            if user_exist:
                u = User.objects.filter(user_email=user_email).update(user_pass=encrypted_pass, user_name=username)
            else:
                u = User.objects.create(user_name=username, user_email=user_email, in_server='imap-mail.outlook.com',
                                        user_pass=encrypted_pass, user_host='outlook', in_port=993,
                                        out_server='smtp-mail.outlook.com', out_port=465)
                u.save()
            request.session['user_email'] = user_email
            uid = db.get_id(User, user_email)
            request.session['user_id'] = uid[0]['user_id']
            request.session['user_pass'] = password
            request.session['host'] = host
            utl.get_imap_labels(request)
            return redirect('mail/inbox')

        elif host == "imap":
            in_server = request.POST['in_server']
            in_port = request.POST['in_port']
            out_server = request.POST['out_server']
            out_port = request.POST['out_port']
            user_exist = User.objects.filter(user_email=user_email)
            if user_exist:
                u = User.objects.filter(user_email=user_email).update(user_pass=encrypted_pass)

            else:
                u = User.objects.create(user_name=username, user_email=user_email, in_server=in_server,
                                        user_pass=encrypted_pass, user_host='imap', in_port=in_port,
                                        out_server=out_server,
                                        out_port=out_port)
                u.save()
            request.session['user_email'] = user_email
            uid = db.get_id(User, user_email)
            request.session['user_id'] = uid[0]['user_id']
            request.session['user_pass'] = password
            request.session['host'] = host
            utl.get_imap_labels(request)
            return redirect('mail/inbox')

    return render(request, "login.html")


def logout(request):
    try:
        del request.session
        return redirect('login')
    except KeyError:
        pass
        return redirect('login')


def mail(request, slug):
    in_mail = 1
    uid = request.session['user_id']
    imap_conn = utl.imap_login(request)
    imap_host = imap_conn[0]
    imap_user = imap_conn[1]
    decoded_pass = imap_conn[2]
    imap_server = imaplib.IMAP4_SSL(imap_host)
    imap_server.login(imap_user, decoded_pass)
    name = slug
    print("." + name + '.')
    host = request.session['host']
    labels = request.session['labels']
    try:
        default_links = request.session['default_links']
        slug_link = slug
        if str(slug) in ['inbox', 'sent', 'draft', 'starred', 'spam', 'trash']:
            slug_link = default_links[slug]



        draft_count = 0
        spam_unseen_data = 0
        sent_unseen_data = 0
        trash_unseen_data = 0
        draft_unseen_data = 0
        unseen_data = 0
        unseen_mails =[]
        sent_unseen_mails = []
        draft_unseen_mails  = []
        trash_unseen_mails  = []
        spam_unseen_mails = []

        if host == 'gmail':
            res, msgs = imap_server.select(default_links['draft'])
            draft_count = int(msgs[0])

            res, mail_msg = imap_server.select(default_links['inbox'], readonly=True)
            return_code, unseen = imap_server.search(None, 'UnSeen')
            unseen_mails = unseen[0].decode().split(" ")
            if unseen_mails == ['']:
                unseen_data = 0
            else:
                unseen_data = len(unseen_mails)

            res, spam_msg = imap_server.select(default_links['spam'], readonly=True)
            return_code, spam_unseen = imap_server.search(None, 'UnSeen')
            spam_unseen_mails = spam_unseen[0].decode().split(" ")
            if spam_unseen_mails == ['']:
                spam_unseen_data = 0
            else:
                spam_unseen_data = len(spam_unseen_mails)

        elif host == "imap":
            res, mail_msg = imap_server.select(default_links['inbox'], readonly=True)
            return_code, unseen = imap_server.search(None, 'UnSeen')
            unseen_mails = unseen[0].decode().split(" ")
            if unseen_mails == ['']:
                unseen_data = 0
            else:
                unseen_data = len(unseen_mails)

            res, mail_msg = imap_server.select(default_links['spam'], readonly=True)
            return_code, unseen_spam = imap_server.search(None, 'UnSeen')
            spam_unseen_mails = unseen_spam[0].decode().split(" ")
            if spam_unseen_mails == ['']:
                spam_unseen_data = 0
            else:
                spam_unseen_data = len(spam_unseen_mails)

            res, mail_msg = imap_server.select(default_links['draft'], readonly=True)
            return_code, unseen_draft = imap_server.search(None, 'UnSeen')
            draft_unseen_mails = unseen_draft[0].decode().split(" ")
            if draft_unseen_mails == ['']:
                draft_unseen_data = 0
            else:
                draft_unseen_data = len(draft_unseen_mails)

            res, mail_msg = imap_server.select(default_links['sent'], readonly=True)
            return_code, unseen_sent = imap_server.search(None, 'UnSeen')
            sent_unseen_mails = unseen_sent[0].decode().split(" ")
            if sent_unseen_mails == ['']:
                sent_unseen_data = 0
            else:
                sent_unseen_data = len(sent_unseen_mails)

            res, mail_msg = imap_server.select(default_links['trash'], readonly=True)
            return_code, unseen_trash = imap_server.search(None, 'UnSeen')
            trash_unseen_mails = unseen_sent[0].decode().split(" ")
            if trash_unseen_mails == ['']:
                trash_unseen_data = 0
            else:
                trash_unseen_data = len(trash_unseen_mails)

        #         ### Searchhh
        # result, data = imap_server.search(None, '(TEXT "server test")')
        # print(data)


        res, messages = imap_server.select(slug_link, readonly=True)
        reslt, starred_ids = imap_server.search(None, 'FLAGGED')
        star_ids = starred_ids[0].decode().split(" ")


        messages = int(messages[0])
        date_n_time = []
        sender = []
        sub = []
        mail = []
        mylist = {}
        show_label = ""
        d_n_t_stamp = ""
        json_list = {}
        json_dump = []
        ids = []

        if messages < 20:
            count = 0
        else:
            count = messages - emails_count

        query = SentMails.objects.filter(user_id_fk=uid).order_by("-m_id_pk").values()
        if host == "imap" and slug == "sent" and query:
            for i in query:
                attachment = i['attachments']
                link = get_attachment_path(request, attachment)
                From_sent = i['rec_mail']
                subject_sent = i['subject']
                body_sent = i['body']
                d_n_t_stamp_sent = i['date_n_time'].partition('.')[0]
                m_id_sent = i['m_id_pk']
                sender.append(From_sent)
                sub.append(subject_sent)
                mail.append(body_sent)
                date_n_time.append(d_n_t_stamp_sent)
                ids.append(m_id_sent)
                json_list[m_id_sent] = [{"msg_uids": m_id_sent, "To": request.session['user_email'], "From": From_sent,
                                         "From_email": From_sent,
                                         "From_uname": From_sent, "subject": subject_sent, "date": d_n_t_stamp_sent,
                                         "output": body_sent, "attachment": attachment, "link": link,
                                         "d_n_t_stamp": d_n_t_stamp_sent, 'show_label': show_label}]

                json_dump = json.dumps(json_list)
            mylist = zip(sender, sub, mail, date_n_time, ids)

        for i in range(messages, count, -1):
            res, msg = imap_server.fetch(str(i), "(RFC822)")
            for response in msg:
                msg_uids = i
                show_label = ""
                if isinstance(response, tuple):
                    if host == "gmail":
                        label = imap_server.fetch(str(i), '(X-GM-LABELS)')
                        label = [x.decode('utf-8') for x in label[1]]
                        label = label[0].split('(')[2].split(')')[0]
                        label = label.replace("\\", "")
                        label = label.replace('"', "")
                        show_label = utl.Convert(label)
                    msg = email.message_from_bytes(response[1])
                    From_email = ""
                    From_uname = ""
                    To = msg["To"]
                    From = msg["From"]

                    if "sent" in slug:
                        From = msg["To"]
                        From_email = imap_user

                    if "<" in From:
                        From_email = From.split('<')[1].split('>')[0]
                        partitioned_string = From.partition('<')
                        From_uname = partitioned_string[0]
                    else:
                        From_email = msg["From"]
                    # if "<" in To and host == "imap":
                    #     To = To.split('<')[1].split('>')[0]
                    dt = ''
                    if 'Delivery-date' in msg:
                        dt = msg['Delivery-date']
                    elif 'Date' in msg:
                        dt = msg['Date']

                    print("dt",dt)

                    # if '+' in dt:
                    #     d_n_t_stamp = dt.partition('+')[0]
                    # elif '-' in dt:
                    #     d_n_t_stamp = dt.partition('-')[0]

                    # print(d_n_t_stamp)
                    date_str = msg.get('date')
                    if date_str != None:
                        date_tuple = email.utils.parsedate_tz(date_str)
                        date = datetime.datetime.fromtimestamp(email.utils.mktime_tz(date_tuple)).date().strftime(
                            '%d %B, %Y')
                    else:
                        date = ""

                    subject = msg["Subject"]
                    body = ""
                    plain_body = ""
                    attachment = ""
                    link = ""

                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_maintype() == 'multipart':
                                continue
                            elif part.get_content_type() == "text/html":
                                body = part.get_payload(decode=True)
                                body = body.decode()
                            elif part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True)
                                body = body.decode()
                                plain_body = body[0:80]

                            if part.get('Content-Disposition') is None:
                                attachment = ''
                            # if part.get('Content-Disposition') is not None:
                            #     open(MEDIA_ROOT + "/" + part.get_filename(), 'wb').write(
                            #         part.get_payload(decode=True))
                            #     attachment = MEDIA_URL + part.get_filename()
                            #     link = get_attachment_path(request, attachment)


                    else:
                        body = body + str(msg.get_payload(decode=True)) + '\n'

                    json_list[msg_uids] = [{"msg_uids": msg_uids, "To": To, "From": From,
                                            "From_email": From_email,
                                            "From_uname": From_uname, "subject": subject, "date": date,
                                            "output": body, "attachment": attachment, "link": link,
                                            "d_n_t_stamp": dt, 'show_label': show_label}]

                    json_dump = json.dumps(json_list)

                    sender.append(From)
                    sub.append(subject)
                    mail.append(plain_body)
                    date_n_time.append(dt)
                    ids.append(msg_uids)
                    msg_ids = []
                    for n in ids:
                        msg_ids.append(str(n))
                    mylist = zip(sender, sub, mail, date_n_time, ids, msg_ids)

        if unseen_mails != ['']:
            for i in unseen_mails:
                mov, data = imap_server.uid('STORE', i, '-FLAGS', '\SEEN')

        if spam_unseen_mails != ['']:
            print(spam_unseen_mails)
            for i in spam_unseen_mails:
                mov, data = imap_server.uid('STORE', i, '-FLAGS', '\SEEN')

        if host == "imap":
            if draft_unseen_mails != ['']:
                for i in draft_unseen_mails:
                    mov, data = imap_server.uid('STORE', i, '-FLAGS', '\SEEN')

        if sent_unseen_mails != ['']:
            for i in sent_unseen_mails:
                mov, data = imap_server.uid('STORE', i, '-FLAGS', '\SEEN')

        if trash_unseen_mails != ['']:
            for i in trash_unseen_mails:
                mov, data = imap_server.uid('STORE', i, '-FLAGS', '\SEEN')


    except Exception as error:
        print('error', error)
        mylist = []
        json_list = {}
        json_dump = []




    data = {'mylist': mylist, 'labels': labels, 'name': name, 'in_mail': in_mail,
            'json_list': json_dump, 'draft_count':draft_count, 'unseen_data':unseen_data,
            'unseen_mails':unseen_mails, 'star_ids':star_ids, 'spam_unseen_mails':spam_unseen_mails,
            'spam_unseen_data':spam_unseen_data, 'host': host, 'sent_unseen_mails':sent_unseen_mails,
            'sent_unseen_data':sent_unseen_data, 'draft_unseen_data':draft_unseen_data,
            'draft_unseen_mails':draft_unseen_mails, 'trash_unseen_data':trash_unseen_data,
            'trash_unseen_mails':trash_unseen_mails}

    return render(request, "app-email.html", data)


def get_attachment_path(request, slug):
    return slug


def move_mails(request):
    default_links = request.session['default_links']
    spam_mailbox = default_links['spam']
    trash_mailbox = default_links['trash']
    inbox_mailbox = default_links['inbox']
    sent_mailbox = default_links['sent']
    accesses = request.POST.getlist('array[]')
    type = request.POST.getlist('type')
    mailbox = request.POST.getlist('mailbox')
    if mailbox[0] not in default_links:
        mail_box = mailbox[0]
    else:
        mail_box = default_links[mailbox[0]]

    imap_conn = utl.imap_login(request)
    imap_host = imap_conn[0]
    imap_user = imap_conn[1]
    decoded_pass = imap_conn[2]
    imap_server = imaplib.IMAP4_SSL(imap_host)
    imap_server.login(imap_user, decoded_pass)
    imap_server.select(mailbox=mail_box, readonly=False)
    resp, items = imap_server.search(None, 'All')

    for i in accesses:
        resp, data = imap_server.fetch(i, "(UID)")
        msg_uid = utl.parse_uid(data[0])
        if mailbox == ['trash']:
            if type[0] == 'inbox':
                result = imap_server.uid('COPY', msg_uid, inbox_mailbox)
                if result[0] == 'OK':
                    mov, data = imap_server.uid('STORE', msg_uid, '+FLAGS', '(\Deleted)')
                    imap_server.expunge()

            elif type[0] == 'sent':
                result = imap_server.uid('COPY', msg_uid, sent_mailbox)
                if result[0] == 'OK':
                    mov, data = imap_server.uid('STORE', msg_uid, '+FLAGS', '(\Deleted)')
                    imap_server.expunge()

            else:
                print('here only')
                mov, data = imap_server.uid('STORE', msg_uid, '+FLAGS', '(\Deleted)')
                imap_server.expunge()

        if type[0] == 'spam':
            result = imap_server.uid('COPY', msg_uid, spam_mailbox)
            if result[0] == 'OK':
                mov, data = imap_server.uid('STORE', msg_uid, '+FLAGS', '(\Deleted)')
                imap_server.expunge()

        elif type[0] == 'trash' or type[0] == 'delete':
            result = imap_server.uid('COPY', msg_uid, trash_mailbox)
            if result[0] == 'OK':
                mov, data = imap_server.uid('STORE', msg_uid, '+FLAGS', '(\Deleted)')
                imap_server.expunge()



    return HttpResponse("Mail moved")

def move_label_mails(request):
    default_links = request.session['default_links']
    m_id = request.POST.getlist('m_id')
    accesses = request.POST.getlist('array[]')
    mailbox = request.POST.getlist('mailbox')
    if mailbox[0] not in default_links:
        mail_box = mailbox[0]
    else:
        mail_box = default_links[mailbox[0]]
    imap_conn = utl.imap_login(request)
    imap_host = imap_conn[0]
    imap_user = imap_conn[1]
    decoded_pass = imap_conn[2]
    imap_server = imaplib.IMAP4_SSL(imap_host)
    imap_server.login(imap_user, decoded_pass)
    imap_server.select(mailbox=mail_box, readonly=False)
    resp, items = imap_server.search(None, 'All')
    if accesses != []:
        type = request.POST['type']
        for i in accesses:
            resp, data = imap_server.fetch(i, "(UID)")
            msg_uid = utl.parse_uid(data[0])
            result = imap_server.uid('COPY', msg_uid, type)
            if result[0] == 'OK':
                mov, data = imap_server.uid('STORE', msg_uid, '+FLAGS', '(\Deleted)')
                imap_server.expunge()
    elif m_id != []:
        type_mail = request.POST['type_mail']
        for i in m_id:
            resp, data = imap_server.fetch(i, "(UID)")
            msg_uid = utl.parse_uid(data[0])
            result = imap_server.uid('COPY', msg_uid, type_mail)
            if result[0] == 'OK':
                mov, data = imap_server.uid('STORE', msg_uid, '+FLAGS', '(\Deleted)')
                imap_server.expunge()

    return HttpResponse("Email moved")

def star_mail(request):
    default_links = request.session['default_links']
    starred_mailbox = default_links['starred']
    star_id = request.POST.getlist('id')
    starred_id = request.POST.get('star_ids').replace('&#x27;', '')
    mailbox = request.POST.getlist('mailbox')
    m_id = request.POST.getlist('m_id')
    
    mail_box = ""

    if mailbox[0] not in default_links:
        mail_box = mailbox[0]
    else:
        mail_box = default_links[mailbox[0]]
    imap_conn = utl.imap_login(request)
    imap_host = imap_conn[0]
    imap_user = imap_conn[1]
    decoded_pass = imap_conn[2]
    imap_server = imaplib.IMAP4_SSL(imap_host)
    imap_server.login(imap_user, decoded_pass)
    imap_server.select(mailbox=mail_box, readonly=False)
    resp, items = imap_server.search(None, 'All')
    if star_id:
        for i in star_id:
            resp, data = imap_server.fetch(i, "(UID)")
            msg_uid = utl.parse_uid(data[0])
            if mailbox==['starred']:
                mov, data = imap_server.uid('STORE', msg_uid, '-FLAGS', '(\Flagged)')
                imap_server.expunge()
            else:
                result = imap_server.uid('COPY', msg_uid, starred_mailbox)

                if result[0] == 'OK':
                    print(msg_uid, i, starred_id)

                    if i not in starred_id:
                        mov, data = imap_server.uid('STORE', i, '+FLAGS', '(\Flagged)')
                        imap_server.expunge()
                    else:
                        mov, data = imap_server.uid('STORE', msg_uid, '-FLAGS', '(\Flagged)')
                        imap_server.expunge()


    elif m_id:
        for i in m_id:
            resp, data = imap_server.fetch(i, "(UID)")
            msg_uid = utl.parse_uid(data[0])

            result = imap_server.uid('COPY', msg_uid, starred_mailbox)
            if result[0] == 'OK':
                mov, data = imap_server.uid('STORE', msg_uid, '+FLAGS', '(\Flagged)')
                imap_server.expunge()

    return HttpResponse("Marked Fav")




def delete_spam_mail(request):
    default_links = request.session['default_links']
    spam_mailbox = default_links['spam']
    trash_mailbox = default_links['trash']
    mailbox = request.POST.getlist('mailbox')
    m_id = request.POST.getlist('m_id')
    id = request.POST.getlist('id')
    print(id, m_id)
    mail_box = ""
    if mailbox[0] not in default_links:
        mail_box = mailbox[0]
    else:
        mail_box = default_links[mailbox[0]]

    imap_conn = utl.imap_login(request)
    imap_host = imap_conn[0]
    imap_user = imap_conn[1]
    decoded_pass = imap_conn[2]
    imap_server = imaplib.IMAP4_SSL(imap_host)
    imap_server.login(imap_user, decoded_pass)
    imap_server.select(mailbox=mail_box, readonly=False)
    resp, items = imap_server.search(None, 'All')

    if id == ['Spam']:
        for i in m_id:
            resp, data = imap_server.fetch(i, "(UID)")
            msg_uid = utl.parse_uid(data[0])

            result = imap_server.uid('COPY', msg_uid, spam_mailbox)
            if result[0] == 'OK':
                mov, data = imap_server.uid('STORE', msg_uid, '+FLAGS', '(\Deleted)')
                imap_server.expunge()
    elif id == ['Trash']:
        for i in m_id:
            resp, data = imap_server.fetch(i, "(UID)")
            msg_uid = utl.parse_uid(data[0])

            result = imap_server.uid('COPY', msg_uid, trash_mailbox)
            if result[0] == 'OK':
                mov, data = imap_server.uid('STORE', msg_uid, '+FLAGS', '(\Deleted)')
                imap_server.expunge()

    else:


        for i in m_id:
            resp, data = imap_server.fetch(i, "(UID)")
            msg_uid = utl.parse_uid(data[0])
                    
            if mailbox == ['trash']:
                print("yes")
                mov, data = imap_server.uid('STORE', msg_uid, '+FLAGS', '(\Deleted)')
                imap_server.expunge()

            else:
                result = imap_server.uid('COPY', msg_uid, trash_mailbox)
                if result[0] == 'OK':
                    mov, data = imap_server.uid('STORE', msg_uid, '+FLAGS', '(\Deleted)')
                    imap_server.expunge()



    return HttpResponse("Email moved")


def compose_mail(request):
    uid = request.session['user_id']
    details = db.get_all_object_from_id(User, uid)
    out_server = details[0]['out_server']
    out_port = details[0]['out_port']
    user_email = details[0]['user_email']
    user_pass = request.session['user_pass']
    id = details[0]['user_host']
    attachment = ''

    rec_emails = []
    if request.method == 'POST':
        rec_email = request.POST['email']
        cc = request.POST.get('cc')
        bcc = request.POST.get('bcc')
        subject = request.POST.get('subject')
        body = request.POST.get('msg')
        attachment = request.FILES.get("attachment")
        port = out_port  # For SSL
        smtp_server = out_server
        password = user_pass
        msg = MIMEMultipart()
        msg['From'] = user_email
        msg['To'] = rec_email
        msg['Subject'] = subject
        date_n_time = datetime.datetime.now()


        rec_emails.append(rec_email)
        if cc != "":
            rec_emails.append(cc)
        if bcc != "":
            rec_emails.append(bcc)


        uploaded_file_url = ''
        if attachment != None:
            fs = FileSystemStorage()
            filename = fs.save(attachment.name, attachment)
            uploaded_file_url = fs.path(filename)

            attach_file_name = uploaded_file_url
            attach_file = open(attach_file_name, 'rb')
            payload = MIMEBase('application', 'octate-stream')
            payload.set_payload((attach_file).read())
            encoders.encode_base64(payload)  # encode the attachment
            payload.add_header('Content-Disposition', 'attachment', filename=attach_file_name)
            msg.attach(payload)

        msg.attach(MIMEText(body, 'html'))
        text = msg.as_string()
        context = ssl.create_default_context()

        with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
            server.login(user_email, password)
            server.sendmail(user_email, rec_emails, text)

        if request.session['host'] == "imap":
            s = SentMails.objects.create(user_id_fk=uid, rec_mail=rec_email, cc=cc, bcc=bcc, subject=subject,
                                         body=body, attachments=uploaded_file_url, date_n_time=date_n_time)
            s.save()

        return redirect('mail/inbox')




def set_msg_as_draft(request):
    imap_conn = utl.imap_login(request)
    imap_host = imap_conn[0]
    imap_user = imap_conn[1]
    decoded_pass = imap_conn[2]
    default_links = request.session['default_links']
    imap_server = imaplib.IMAP4_SSL(imap_host)
    imap_server.login(imap_user, decoded_pass)
    new_message = email.message.Message()

    if request.method == "POST":
        To = request.POST.get("to")
        cc = request.POST.get("cc")
        bcc = request.POST.get("bcc")
        subject = request.POST.get("subject")
        body = request.POST.get("body")

    new_message["From"] = imap_user
    new_message["To"] =  To
    new_message["Subject"] = subject
    new_message.set_payload(body)
    new_message.set_charset(email.charset.Charset("utf-8"))
    encoded_message = str(new_message).encode("utf-8")
    imap_server.append(default_links['draft'], '', imaplib.Time2Internaldate(time.time()), encoded_message)

    return redirect('mail/inbox')

def mark_mail_as_read(request):
    imap_conn = utl.imap_login(request)
    imap_host = imap_conn[0]
    imap_user = imap_conn[1]
    decoded_pass = imap_conn[2]
    default_links = request.session['default_links']
    host = request.session['host']
    imap_server = imaplib.IMAP4_SSL(imap_host)
    imap_server.login(imap_user, decoded_pass)
    if request.method == "POST":
        msg_id = request.POST.get('msg_id')
        mailbox = request.POST.get('mailbox')

        if mailbox == 'spam':
            imap_server.select(default_links['spam'])
            imap_server.store(msg_id, '+FLAGS', '\Seen')
        elif mailbox == 'inbox':
            imap_server.select(default_links['inbox'])
            imap_server.store(msg_id, '+FLAGS', '\Seen')
        if host == "imap":
            if mailbox == 'sent':
                imap_server.select(default_links['sent'])
                imap_server.store(msg_id, '+FLAGS', '\Seen')
            if mailbox == 'trash':
                imap_server.select(default_links['trash'])
                imap_server.store(msg_id, '+FLAGS', '\Seen')
            if mailbox == 'draft':
                imap_server.select(default_links['draft'])
                imap_server.store(msg_id, '+FLAGS', '\Seen')


    return HttpResponse("Mail Seen")

