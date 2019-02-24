from django.conf import settings
from django.contrib.sites.models import Site
from clublink.cms.models import CorpImage, CorpSnippet, CorpPage


'''
export AWS_ACCESS_KEY_ID='AKIAIKNM63IX2LE5V4UA'
export AWS_SECRET_ACCESS_KEY='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'
aws s3 sync s3://production-club s3://stage-club
'''

def boto_move(sourceBucket, targetBucket):
    # copying form S3 buckets using new boto
    #https://stackoverflow.com/a/43233507
    import boto3
    s3 = boto3.resource(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
    src = s3.Bucket(sourceBucket)

    for o in src.objects.all():
        key={'Bucket':sourceBucket, 'Key':o.key}
        s3.meta.client.copy(key, targetBucket, o.key)



def move_individual_page(p, site, parent=None):

    spacer = '\t' if parent else ''
    print ('{}Start {}'.format(spacer, p.id))

    images = p.images.values('pk')
    snippets = p.snippets.values('pk')
    children = p.children.values('pk')

    p.pk = None
    p.parent = parent
    p.site = site

    # if children:
    #     import pdb; pdb.set_trace()

    p.save()

    # if children:
    #     import pdb; pdb.set_trace()


    imgs = CorpImage.objects.filter(pk__in=images)
    for i in imgs:
        i.pk = None
        i.page = p
        #print(i.pk)
        i.save()

    snips = CorpSnippet.objects.filter(pk__in=snippets)

    for s in snips:
        s.pk = None
        s.page = p
        #print(s.pk)
        s.save()

    if children:
        print('\n\nMoving Children!!!')
        for child in CorpPage.objects.filter(pk__in=children):
            move_individual_page(child, site, p)


def move_pages():
    # For all pages, images and snippets already in the DB, we want to move them over

    from django.contrib.sites.models import Site

    canada = Site.objects.first()
    usa = Site.objects.last()

    for p in canada.corppage.filter(parent=None):
        move_individual_page(p, usa)


def import_calendar(filepath, clubId):
    '''
    Default club calendar export from ClubLink
    '''
    mapping_dict = {
        'TYPE': {'modelField': 'type', 'type': 'string'},
        'Subject': {'modelField': 'name', 'type': 'string'},
        'Start Date': {'modelField': 'start_date', 'type': 'date'},
        'Start Time': {'modelField': 'start_time', 'type': 'time'},
        'End Date': {'modelField': 'end_date', 'type': 'date'},
        'End Time': {'modelField': 'end_time', 'type': 'time'},
        'Description': {'modelField': 'description', 'type': 'string'}
    }

    import csv
    from clublink.clubs.models import Club, ClubEvent
    from datetime import datetime

    club = Club.objects.get(id=clubId)

    with open(filepath) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            data = {'club_id': clubId}
            for k, v in row.items():
                if k in mapping_dict.keys():

                    dictkey = mapping_dict[k]['modelField']

                    if mapping_dict[k]['type'] == 'date':
                        dictvalue = datetime.strptime(v, '%x').date()
                    elif mapping_dict[k]['type'] == 'time':
                        dictvalue = datetime.strptime(v, '%I:%M %p').time()
                    elif k == 'TYPE':
                        dictvalue = {
                            'MEMBER': ClubEvent.MEMBER_EVENT,
                            'NOTICE': ClubEvent.NOTICE
                            }[v.strip()]
                    else:
                        dictvalue = v

                    data[dictkey] = dictvalue

            event = ClubEvent.objects.create(
                **data
            )
            print(event.id)

def migrate_users_json():
    from clublink.users.models import UserCategory, UserType, User
    import csv, json

    with open('users.json', 'r') as file:
        data = json.load(file)

    id_mapping = ['home_club', 'option_club', 'type', 'home_club_alternate_1', 'home_club_alternate_2', 'category']

    problems = []

    for d in data:
        try:
            fields = d.get('fields')
            fields.pop('groups', None)
            fields.pop('user_permissions', None)

            for f in id_mapping:
                if fields[f]:
                    fields['{}_id'.format(f)] = fields[f]
                    fields.pop(f, None)

            user = User.objects.filter(pk=d['pk'])
            if user:
                user.update(**fields)
            else:
                fields['pk'] = d['pk']
                user = User.objects.create(**fields)

        except Exception as e:
            print('{}'.format(d['pk']))
            problems.append(d)
            print(e)


def sync_model_instances(ModelClass, fromdbName, todbName, update_existing=True):

    # Update pks that are the same
    current_existing = ModelClass.objects.using(todbName).values_list('pk', flat=True)
    print('\n==================================')
    print('{} items in current database'.format(current_existing.count()))
    print('==================================\n')

    fromdb = ModelClass.objects.using(fromdbName).all()
    fromdb_existing = fromdb.filter(pk__in=list(current_existing))
    fromdb_new = fromdb.exclude(pk__in=list(current_existing))
    print('\n==================================')
    print('{} items in {} database'.format(fromdb.count(), fromdbName))
    print('\t\t--> Existing: {}'.format(fromdb_existing.count()))
    print('\t\t--> New: {}'.format(fromdb_new.count()))
    print('==================================\n')

    update_problems = []
    if update_existing:
        print('\n==================================')
        print('Update {} existing objects already in database'.format(fromdb_existing.count()))

        for l in fromdb_existing:
            try:
                fromdb_obj = ModelClass.objects.using(fromdbName).get(pk=l.pk)

                fields = {k:v for k,v in fromdb_obj.__dict__.items() if '_' not in k[:2]}

                new_obj = ModelClass.objects.using(todbName).filter(pk=l.pk).update(**fields)
            except Exception as e:
                print(e)
                update_problems.append(l)

        print('\t\t--> DONE!')
        print('==================================\n')


    print('\n==================================')
    print('Create {} new objects from {} db'.format(fromdb_new.count(), fromdbName))
    create_problems = []
    for l in fromdb_new:
        try:
            l.pk = None
            l.save(using=todbName, force_insert=True)
        except Exception as e:
            print(e)
            create_problems.append(l)
    print('\t\t--> DONE!')
    print('==================================\n')

    if create_problems or update_problems:
        print('\n==================================')
        print('{} problems encountered!'.format(len(update_problems) + len(create_problems)))
        print('\t\t--> Update: {}'.format(len(update_problems)))
        print('\t\t--> Create: {}'.format(len(create_problems)))
        print('==================================\n')
    return {
        'update': update_problems,
        'create': create_problems
    }
