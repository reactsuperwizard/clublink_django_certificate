from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


def send_rsvp_email_to_member(rsvp, bywhom=None):
    subject = 'Reservation Confirmation: {} {}'.format(
        rsvp.event.club.name,
        rsvp.event.name
        )

    context = {
        'rsvp': rsvp,
        'bywhom': bywhom
    }

    message = render_to_string(
        'clubs/email/member_rsvp.txt', context=context)
    message_html = render_to_string(
        'clubs/email/member_rsvp.jinja', context=context)

    to = [rsvp.user.email]

    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL_ADDRESS')

    email = EmailMultiAlternatives(
        subject=subject, body=message, to=to,
        from_email='ClubLink <{}>'.format(from_email))

    email.attach_alternative(message_html, 'text/html')

    email.send()


def send_rsvp_email_to_admin(rsvp, bywhom=None):
    if not rsvp.event.club.calendar_rsvp_email:
        return

    subject = 'Reservation: {} {} ({} {}: {})'.format(
        rsvp.event.club.name,
        rsvp.event.name,
        rsvp.user.first_name,
        rsvp.user.last_name,
        rsvp.user.membership_number
        )

    context = {
        'rsvp': rsvp,
        'bywhom': bywhom
    }

    message = render_to_string(
        'clubs/email/admin_rsvp.txt', context=context)
    message_html = render_to_string(
        'clubs/email/admin_rsvp.jinja', context=context)

    to = [rsvp.event.club.calendar_rsvp_email]
    if rsvp.event.email:
        to = [rsvp.event.email]
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL_ADDRESS')

    email = EmailMultiAlternatives(
        subject=subject, body=message, to=to,
        from_email='ClubLink <{}>'.format(from_email))

    email.attach_alternative(message_html, 'text/html')

    email.send()


def send_cancel_rsvp_email_to_member(rsvp, bywhom=None):
    subject = 'Reservation Cancelled: {} {}'.format(
        rsvp.event.club.name,
        rsvp.event.name
        )

    context = {
        'rsvp': rsvp,
        'bywhom': bywhom
    }

    message = render_to_string(
        'clubs/email/member_cancel_rsvp.txt', context=context)
    message_html = render_to_string(
        'clubs/email/member_cancel_rsvp.jinja', context=context)


    to = [rsvp.user.email]
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL_ADDRESS')

    email = EmailMultiAlternatives(
        subject=subject, body=message, to=to,
        from_email='ClubLink <{}>'.format(from_email))

    email.attach_alternative(message_html, 'text/html')

    email.send()


def send_cancel_rsvp_email_to_admin(rsvp, bywhom=None):
    if not rsvp.event.club.calendar_rsvp_email:
        return

    subject = 'Cancellation: {} {} ({} {}: {})'.format(
        rsvp.event.club.name,
        rsvp.event.name,
        rsvp.user.first_name,
        rsvp.user.last_name,
        rsvp.user.membership_number
        )

    context = {
        'rsvp': rsvp,
        'bywhom': bywhom
    }

    message = render_to_string(
        'clubs/email/admin_cancel_rsvp.txt', context=context)
    message_html = render_to_string(
        'clubs/email/admin_cancel_rsvp.jinja', context=context)

    to = [rsvp.event.club.calendar_rsvp_email]
    if rsvp.event.email:
        to = [rsvp.event.email]
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL_ADDRESS')

    email = EmailMultiAlternatives(
        subject=subject, body=message, to=to,
        from_email='ClubLink <{}>'.format(from_email))

    email.attach_alternative(message_html, 'text/html')

    email.send()
