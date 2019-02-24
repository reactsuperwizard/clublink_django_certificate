from django.shortcuts import render


def gift_cards(request):
    return render(request, 'gift_cards/home.jinja')
