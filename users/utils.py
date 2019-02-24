import time

from urllib.request import quote
from urllib.parse import urljoin

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.shortcuts import reverse
from django.template.loader import render_to_string

from clublink.users.models import User


def send_website_announcement_email(user, **kwargs):
    club = user.option_club or user.home_club
    base_url = 'https://{}.clublink.ca/'.format(club.slug)
    path = '{}?token={}'.format(reverse('login.reset', urlconf='clublink.urls.clubs'),
                                quote(user.generate_reset_token()))
    reset_url = urljoin(base_url, path)

    subject = 'New website announcement'

    context = {
        'user': user,
        'club': club,
        'reset_url': reset_url,
    }

    locale = kwargs.get('locale', user.preferred_language).lower()

    message = render_to_string(
        'users/email/new_website_{}.txt'.format(locale), context=context)
    message_html = render_to_string(
        'users/email/new_website_{}.jinja'.format(locale), context=context)

    to = [kwargs.get('to')]
    from_email = getattr(settings, 'MEMBER_SERVICES_EMAIL_ADDRESS')

    email = EmailMultiAlternatives(
        subject=subject, body=message, to=to,
        from_email='ClubLink Member Services <{}>'.format(from_email))

    email.attach_alternative(message_html, 'text/html')

    email.send()


def send_all_website_announcement_emails():
    users = User.objects.filter(status='A', password='', membership_number__startswith='1',
                                email__contains='@')
    users = users.exclude(email=None).exclude(is_staff=1).exclude(is_superuser=1)
    users = users.exclude(invited=True)
    users = list(users)

    total = len(users)
    sent = 0
    stats = {
        'en': 0,
        'fr': 0,
        'failed': 0,
    }

    while sent < total:
        start = time.time()
        counter = 0
        while counter < 35 and counter + sent < total:
            try:
                u = users[sent + counter]
            except IndexError:
                break
            else:
                try:
                    send_website_announcement_email(u, to=u.email)
                except Exception as e:
                    print(e)
                    stats['failed'] += 1
                else:
                    u.invited = True
                    u.save()
                    if u.preferred_language in stats:
                        stats[u.preferred_language] += 1
                counter += 1
        sent += counter
        end = time.time()
        remain = start - end + 1
        print('Sent {} of {}'.format(sent, total))
        if remain > 0:
            time.sleep(remain)

    print(stats)
