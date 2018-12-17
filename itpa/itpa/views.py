import re
import os

from rest_framework import viewsets
from django.conf import settings

from rest_framework.decorators import api_view, renderer_classes, detail_route, list_route, parser_classes
from rest_framework import response, schemas, status

from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User

ITPA_ADMIN_TOKEN = os.environ.get('ITPA_ADMIN_TOKEN', 'ofiowhsudhfzdllk')
ITPA_VIDEO_RECORDER_TOKEN = os.environ.get('VIDEO_RECORDER_TOKEN', 'sfssdfsdfsdf')

from itpa.utils import (validate_email, validate_password, get_user_rights, get_user_and_token_from_token_key,
    get_user_by_user_name, set_needs_confirmation_code, create_new_user_account, grant_access, check_confirmation_code, send_confirmation_code,
    user_can_admin_itpa,
    fill_full_user_rights,
    fill_recorder_user_rights,
    )

MAX_USERS_IN_USER_LIST = 1000

@api_view(['GET'])
def user_list(request):
    user_list_obj = None
    try:
        token_key = request.GET.get("token", None)
        if token_key != None:
            ok = token_key == ITPA_ADMIN_TOKEN
            if not ok:
                user, _ = get_user_and_token_from_token_key(token_key)
                ok = user_can_admin_itpa(user)
            if ok:
                user_list_obj = [
                    {
                        'user_name': user.username,
                        'email_confirmed': user.profile.email_confirmed == True,
                        'email_confirmation_code_sent': user.profile.email_confirmation_code_sent,
                    } for user in User.objects.order_by('-last_login')[:MAX_USERS_IN_USER_LIST]
                ]
    except Exception as e:
        print('user_list exception: ' + str(e))
        user_list_obj = None

    return response.Response(user_list_obj if user_list_obj != None else {})

@api_view(['GET'])
def user_rights(request):
    user_rights_obj = None
    try:
        token_key = request.GET.get("token", None)
        if token_key != None:
            if token_key == ITPA_ADMIN_TOKEN:
                user_rights_obj = fill_full_user_rights()
            elif token_key == ITPA_VIDEO_RECORDER_TOKEN:
                user_rights_obj = fill_recorder_user_rights()
            else:
                user, _ = get_user_and_token_from_token_key(token_key)
                user_rights_obj = get_user_rights(user)
    except Exception as e:
        print('user_rights: ' + str(e))
        user_rights_obj = None

    return response.Response(user_rights_obj if user_rights_obj != None else {})

class CustomAuthToken(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        token = None
        user_id = None
        user_name = None
        email = None
        msg = "ok"
        user_rights = None
        try:
            serializer = self.serializer_class(data=request.data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            user = serializer.validated_data['user']
            #token, created = Token.objects.get_or_create(user=user)
            token, _ = Token.objects.get_or_create(user=user)
            token = token.key
            user_id = user.pk
            user_name = user.username
            email = user.email
            user_rights = get_user_rights(user)
        except Exception as e:
            user_rights = token = user_id = email = user_name = None
            can_add = can_delete = False;
            msg = str(e)
        return response.Response({
            'msg': msg,
            'token': token,
            'user_id': user_id,
            'email': email,
            'user_name': user_name,
            'user_rights': user_rights,
        })

@api_view(['GET'])
def hello(request):
    return response.Response({
        'hello': 'world'
    })

@api_view(['GET'])
def login(request):
    access_result = {
        #'token': 'tokenvalue',
        #'codeSent': False,
        #'needsCode': False,
        #'wrongCode': False,
        #'expiredCode': False,
        #'accessGranted': False,
        #'invalidParameters': False,
        #'invalidEmail': False,
        #'invalidPassword:': False,
        'message': '',
    }
    try:
        user_name = request.GET.get("user_name", None)
        password = request.GET.get("password", None)
        if (user_name != None and password != None):
            if validate_email(user_name):
                validate_password_message = validate_password(password)
                if validate_password_message == None:
                    user = get_user_by_user_name(user_name)
                    if user != None:
                        if user.is_active:
                            access_was_granted = False
                            if user.profile.email_confirmed:
                                if user.check_password(password):
                                    access_was_granted = grant_access(request, user, access_result, None)
                            if not access_was_granted:
                                user_was_issued_confirmation_code = user.profile.email_confirmation_code != ''
                                confirmation_code = request.GET.get("confirmationCode", None)
                                has_confirmation_code = user_was_issued_confirmation_code and confirmation_code != None and len(confirmation_code) > 0
                                if has_confirmation_code:
                                    check_confirmation_code(request, confirmation_code, user, password, access_result)
                                else:
                                    asked_for_confirmation_code = request.GET.get("askedForConfirmationCode", False)
                                    if asked_for_confirmation_code:
                                        send_confirmation_code(request, user, user_name, access_result)
                                    else:
                                        set_needs_confirmation_code(access_result)
                        else:
                            access_result['message'] = 'Please try again later'
                    else:
                        create_new_user_account(user_name, password, access_result)
                else:
                    access_result['invalidPassword'] = True
                    access_result['message'] = validate_password_message
            else:
                access_result['invalidEmail'] = True
                access_result['message'] = 'This does not seem to be a valid email address'
        else:
            access_result['invalidParameters'] = True
            access_result['message'] = 'Invalid parameters'
    except Exception as e:
        access_result['invalidParameters'] = True
        access_result['message'] = 'Exception error'
        print('login exception: ' + str(e))

    if access_result['message'] == '':
        access_result['invalidParameters'] = True
        access_result['message'] = 'Unexpected error'

    return response.Response(access_result)
