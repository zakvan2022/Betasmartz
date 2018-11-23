# -*- coding: utf-8 -*-
import json
import stripe
import logging
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from goal.models import Transaction

logger = logging.getLogger('api.v1.stripe_webhooks')
stripe.api_key = settings.STRIPE_API_SECRET


@require_POST
@csrf_exempt
def stripe_webhook(request):
    event = json.loads(request.body.decode('utf-8'))

    # if event success - find matching transaction and mark success
    if event['type'] == 'charge.succeeded':
        logger.info('Charge succeeded id %s amount %s' % (event['data']['object']['id'], event['data']['object']['amount']))
        try:
            trans = Transaction.objects.get(stripe_id=event['data']['object']['id'])
        except:
            logger.error('Charge succeeded from stripe id %s but Transaction not found' % event['data']['object']['id'])
            return HttpResponse(status=200)
        trans.status = Transaction.STATUS_EXECUTED
        trans.save()


    elif event['type'] == 'charge.failed':
        logger.error('Charge failed id %s amount %s' % (event['data']['object']['id'], event['data']['object']['amount']))
        logger.error('Stripe failure_code %s failure_message %s' % (event['data']['object']['failure_code'], event['data']['object']['failure_message']))
        try:
            trans = Transaction.objects.get(stripe_id=event['data']['object']['id'])
        except:
            logger.error('Charge failed from stripe id %s but Transaction not found' % event['data']['object']['id'])
            return HttpResponse(status=200)
        trans.status = Transaction.STATUS_FAILED
        trans.save()

    elif event['type'] == 'charge.pending':
        logger.info('Charge pending id %s amount %s' % (event['data']['object']['id'], event['data']['object']['amount']))

    elif event['type'] == 'transfer.paid':
        logger.info('Transfer succeeded id %s amount %s' % (event['data']['object']['id'], event['data']['object']['amount']))
        try:
            trans = Transaction.objects.get(stripe_id=event['data']['object']['id'])
        except:
            logger.error('Transfer paid from stripe id %s but Transaction not found' % event['data']['object']['id'])
            return HttpResponse(status=200)
        trans.status = Transaction.STATUS_EXECUTED
        trans.save()

    elif event['type'] == 'transfer.failed':
        logger.error('Transfer failed id %s amount %s' % (event['data']['object']['id'], event['data']['object']['amount']))
        logger.error('Stripe failure_code %s failure_message %s' % (event['data']['object']['failure_code'], event['data']['object']['failure_message']))
        try:
            trans = Transaction.objects.get(stripe_id=event['data']['object']['id'])
        except:
            logger.error('Transfer failed from stripe id %s but Transaction not found' % event['data']['object']['id'])
            return HttpResponse(status=200)
        trans.status = Transaction.STATUS_FAILED
        trans.save()

    elif event['type'] == 'transfer.reversed':
        logger.info('Transfer reversed id %s amount %s' % (event['data']['object']['id'], event['data']['object']['amount']))

    return HttpResponse(status=200)
