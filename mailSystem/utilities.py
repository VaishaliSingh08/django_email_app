import re
import imaplib
from cryptography.fernet import Fernet
from proj1 import database_functions as db
from mailSystem.models import User



key = Fernet.generate_key()
fernet = Fernet(key)

def imap_login(request):
    uid = request.session['user_id']
    details = db.get_all_object_from_id(User, uid)
    imap_host = details[0]['in_server']
    imap_user = details[0]['user_email']
    imap_pass = details[0]['user_pass']
    decoded_pass = request.session['user_pass']
    user_host = details[0]['user_host']
    cred_list = [ imap_host, imap_user, decoded_pass]

    return cred_list

def decoded_password(request):
    uid = request.session['user_id']
    details = db.get_all_object_from_id(User, uid)
    user_pass = details[0]['user_pass']
    encode_pass = bytes(user_pass, 'utf-8')
    decrypted_pass = my_decrypt(key, encode_pass)
    decoded_pass = decrypted_pass.decode()

    return decoded_pass

def my_encrypt(key, data):
    f = Fernet(key)
    return f.encrypt(data)

def my_decrypt(key, data):
    f = Fernet(key)
    return f.decrypt(data)

def Diff(li1, li2):
    return list(set(li1) - set(li2)) + list(set(li2) - set(li1))

def get_gmail_labels(request):
    imap_conn = imap_login(request)
    imap_host = imap_conn[0]
    imap_user = imap_conn[1]
    decoded_pass = imap_conn[2]

    imap_server = imaplib.IMAP4_SSL(imap_host)
    imap_server.login(imap_user, decoded_pass)
    all_folders = [(i.decode().split(' "/" '))[1] for i in imap_server.list()[1]]
    default_folders = ['"INBOX"',
                       '"[Gmail]/Sent Mail"',
                       '"[Gmail]/Drafts"',
                       '"[Gmail]/Starred"',
                       '"[Gmail]/Spam"',
                       '"[Gmail]/Trash"',
                       '"[Gmail]"',
                       '"[Gmail]/All Mail"',
                       '"[Gmail]/Important"'
                       ]
    if '"[Gmail]/Trash"' in all_folders:
        default_folders[5] = '"[Gmail]/Trash"'
    elif '"[Gmail]/Bin"' in all_folders:
        default_folders[5] =  '"[Gmail]/Bin"'
    
    default_links = {'inbox' :default_folders[0], 'sent' : default_folders[1], 'draft' : default_folders[2],
                     'starred' : default_folders[3], 'spam' : default_folders[4], 'trash' : default_folders[5]}
    request.session['default_links'] = default_links

    labels = Diff(default_folders, all_folders)
    final_labels = [i.strip('" "') for i in labels]
    request.session['labels'] = final_labels
    return final_labels

def get_imap_labels(request):
    imap_conn = imap_login(request)
    imap_host = imap_conn[0]
    imap_user = imap_conn[1]
    decoded_pass = imap_conn[2]
    imap_server = imaplib.IMAP4_SSL(imap_host)
    imap_server.login(imap_user, decoded_pass)

    oper = ["*", ".", "/", ":", ";", "&", "%", "^", "#"]
    all_folders = []
    skip_folders = ['spam', 'Spam','trash', 'Trash', 'junk', 'Junk', 'Bulk Mail','Bulk mail', 'all mail','All Mail',
                    'All mail', 'all Mail','starred', 'Starred', 'Archive', 'archive', 'draft', 'Draft', 'Drafts', 'Notes', 'notes',
                    'outbox', 'Outbox','drafts', 'Sent', 'sent', 'deleted', 'Deleted']
    default_links = {'inbox': 'inbox', 'sent': '', 'draft': '',
                     'starred': '', 'spam': '', 'trash':''}

    for folder in imap_server.list()[1]:
        matching = [value for value in str(folder) if any(op in value for op in oper)]
        l = folder.decode().split(matching[0], 1 )
        all_folders.append((l[1].strip('" "')))

    if 'Inbox' in all_folders:
        all_folders.remove('Inbox')
    if 'INBOX' in all_folders:
        all_folders.remove('INBOX')
    if 'inbox' in all_folders:
        all_folders.remove('inbox')


    for fold in skip_folders :
        element = [string for string in all_folders if fold in string]
        if element:
            if fold in ['spam','Spam', 'junk', 'Junk'] and default_links['spam'] == '':
                default_links['spam'] = element[0]
            elif fold in ['Sent', 'sent'] and default_links['sent'] == '':
                default_links['sent'] = element[0]
            elif fold in ['Trash', 'trash', 'Deleted', 'deleted'] and default_links['trash'] == '':
                default_links['trash'] = element[0]
            elif fold in ['Starred', 'starred'] and default_links['starred'] == '':
                default_links['starred'] = element[0]
            elif fold in ['Draft', 'draft', 'Drafts', 'drafts'] and default_links['draft'] == '':
                default_links['draft'] = element[0]

            all_folders.remove(element[0])

    request.session['default_links'] = default_links
    request.session['labels'] = all_folders
    return all_folders


pattern_uid = re.compile('\d+ \(UID (?P<uid>\d+)\)')
def parse_uid(data):
    d = data.decode('utf-8')
    match = pattern_uid.match(d)
    return match.group('uid')


def get_body(msg):
    if msg.is_multipart():
        return get_body(msg.get_payload(0))
    else:
        return msg.get_payload(None, True)


def Convert(string):
    li = list(string.split(" "))
    return li
