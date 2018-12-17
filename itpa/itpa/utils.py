import re
import time
from datetime import datetime
from random import randint

from django.utils import timezone

from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User
from django.contrib.auth import login

from django.core.mail import send_mail

import itpa.settings

def random_with_N_digits(n):
    range_start = 10**(n-1)
    range_end = (10**n)-1
    return randint(range_start, range_end)

EMAIL_PATTERN = "^[_A-Za-z0-9-\\+]+(\\.[_A-Za-z0-9-]+)*@[A-Za-z0-9-]+(\\.[A-Za-z0-9]+)*(\\.[A-Za-z]{2,})$"

def validate_email(email):
    result = False
    try: result = re.match(EMAIL_PATTERN, email)
    except: result = False
    return result

MIN_PASSWORD_LEN = 8
MAX_PASSWORD_LEN = 12

password_length_error = "Password length must be between " + str(MIN_PASSWORD_LEN) + " and " + str(MAX_PASSWORD_LEN) + " characters"
password_content_error = "Pasword must contain upper and lower case letters, and at least one character that is not a letter";

def validate_password(password):
    result = None
    try:
        if (password != None):
            len_password = len(password)
            if (len_password < MIN_PASSWORD_LEN or len_password > MAX_PASSWORD_LEN):
                result = password_length_error;
            else:
                containsNonAlphaNum = False
                containsUpper = False
                containsLower = False
                containsDigit = False
                for i in range(0, len_password):
                    p = password[i]
                    if (p.isdigit()): containsDigit = True
                    elif (p.isupper()): containsUpper = True
                    elif (p.islower()): containsLower = True
                    else: containsNonAlphaNum = True
                if (not(containsUpper and containsLower and (containsDigit or containsNonAlphaNum))):
                    result = password_content_error;
    except Exception as e:
        print('validate_password exception: ' + str(e))
        result = password_content_error

    return result

def get_user_by_user_name(user_name):
    user = None
    try: user = User.objects.get(username=user_name)
    except: user = None
    return user

def user_belongs_to_group(user, group_name):
    belongs = False
    try: belongs = user != None and user.is_authenticated() and user.groups.filter(name=group_name).exists()
    except: belongs = False
    return belongs

def get_token_from_token_key(token_key):
    token = None
    try: token = Token.objects.get(pk=token_key)
    except: token = None
    return token

def get_user_and_token_from_token_key(token_key):
    user = None
    token = get_token_from_token_key(token_key)
    if token != None:
        try: user = User.objects.get(pk=token.user_id)
        except: user = None
    return user, token

def user_can_admin_itpa(user): return user_belongs_to_group(user, 'Can admin itpa')
def user_can_edit_parking_places(user): return user_belongs_to_group(user, 'Can edit parking places')

def fill_user_rights(user_name, is_user = False, can_admin_itpa = False, can_edit_parking_places = False, can_record_video = False):
    return {
        'user_name': user_name,
        'is_user': is_user,
        'can_admin_itpa': can_admin_itpa,
        'can_edit_parking_places': can_edit_parking_places,
        'can_record_video': can_record_video or can_admin_itpa,
    }

def fill_full_user_rights():
    return fill_user_rights(is_user=True,can_admin_itpa=True,can_edit_parking_places=True, can_record_video=True, user_name='admin')

def fill_recorder_user_rights():
    return fill_user_rights(is_user=True,can_admin_itpa=False,can_edit_parking_places=False, can_record_video=True, user_name='video-recorder')

def get_user_rights(user):
    is_user = can_admin_itpa = can_edit_parking_places = False
    if user != None:
        is_user = True
        can_admin_itpa = user_can_admin_itpa(user)
        can_edit_parking_places = True if can_admin_itpa else user_can_edit_parking_places(user)
    return fill_user_rights(user_name=user.username, is_user=is_user,can_admin_itpa=can_admin_itpa,can_edit_parking_places=can_edit_parking_places)

def set_needs_confirmation_code(access_result):
    try:
        access_result['needsCode'] = True
        access_result['message'] = 'A confirmation code is required'
    except Exception as e:
        print('set_needs_confirmation_code exception: ' + str(e))

def create_new_user_account(user_name, password, access_result):
    try:
        user = User.objects.create_user(user_name, None, password)
        user.profile.email_confirmation_code_sent = None
        user.save()
        set_needs_confirmation_code(access_result)
    except Exception as e:
        access_result['message'] = 'Failed to create new user account'
        print('create_new_user_account exception: ' + str(e))

def grant_access(request, user, access_result, updated_password = None):
    access_granted = False
    try:
        user_profile = user.profile
        user.profile.email_confirmed = True
        if updated_password != None:
            #print('******CHANGED PASSWORD TO: ' + updated_password)
            user.set_password(updated_password)
        user.save()
        if updated_password != None:
            #https://stackoverflow.com/questions/5250230/why-is-my-django-password-change-not-sticking
            user = User.objects.get(profile = user_profile)
            """
            if user.check_password(updated_password): print('change password worked')
            else: print('change password failed')
            """
        login(request, user)
        token, _ = Token.objects.get_or_create(user=user)
        token = token.key
        access_result['token'] = token
        access_result['message'] = 'Welcome'
        access_granted = access_result['accessGranted'] = True
    except Exception as e:
        access_granted = False
        print('grant_access exception: ' + str(e))
    return access_granted

DELAY_CHECK_CONFIRMATION_CODE = 1
NUMBER_OF_MINUTES_BETWEEN_SENDING_CONFIRMATION_CODES = 30
NDIGITS_CONFIRMATION_CODE = 6

def make_confirmation_code():
    return str(random_with_N_digits(NDIGITS_CONFIRMATION_CODE))

def check_code_sent_recently(user):
    result = False
    last_sent = user.profile.email_confirmation_code_sent
    time_now = timezone.now()
    if last_sent != None:
        minutes_diff = (time_now - last_sent).total_seconds() / 60.0
        #print('check_code_sent_recently: minutes_diff == ' + str(minutes_diff))
        result = minutes_diff <= NUMBER_OF_MINUTES_BETWEEN_SENDING_CONFIRMATION_CODES
    return result

def check_confirmation_code(request, confirmation_code, user, password, access_result):
    try:
        time.sleep(DELAY_CHECK_CONFIRMATION_CODE)
        if check_code_sent_recently(user):
            if user.profile.email_confirmation_code == confirmation_code:
                grant_access(request, user, access_result, password)
            else:
                access_result['message'] = 'Confirmation code does not match'
                access_result['wrongCode'] = True
        else:
            access_result['message'] = 'Confirmation code has expired'
            access_result['expiredCode'] = True
    except Exception as e:
        access_result['message'] = ''
        print('check_confirmation_code exception: ' + str(e))

def send_confirmation_code(request, user, user_email, access_result):
    try:
        if check_code_sent_recently(user):
            access_result['message'] = 'A confirmation code was recently sent, check your inbox and spam folders'
        else:
            access_result['message'] = 'A confirmation code was sent'
            cc = make_confirmation_code()
            print('send_confirmation_code will send code: ' + str(cc))
            message = "Your confirmation code is: " + str(cc)
            message +="\n\nThis email was sent from a notification-only address that cannot accept incoming email. Please do not reply to this message.\n";
            send_mail(
                'ITPA Confirmation Code',
                message,
                itpa.settings.EMAIL_HOST_USER,
                [user_email],
                fail_silently=False
            )
            user.profile.email_confirmation_code = cc
            user.profile.email_confirmation_code_sent = timezone.now()
            user.save();
        access_result['codeSent'] = True
    except Exception as e:
        access_result['message'] = 'Unable to send confirmation code by email'
        print('send_confirmation_code exception: ' + str(e))

