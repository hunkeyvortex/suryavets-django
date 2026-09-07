"""Link verified source pack listings without moving variant/order/ledger identities."""
import json
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from shop.models import Product, ProductVariant, CRMActivity
from shop.services.pack_families import candidates


class Command(BaseCommand):
    help='Audit and optionally group unambiguous existing pack listings; never creates invented sizes/prices.'
    def add_arguments(self,parser):
        parser.add_argument('--apply',action='store_true')
        parser.add_argument('--report',required=True)

    @transaction.atomic
    def handle(self,*args,**options):
        products=list(Product.objects.select_for_update().prefetch_related('variants','images','collections','pet_categories').order_by('slug'))
        records=[]; applied=0
        for label,members,packs,reason in candidates(products):
            if any(p.variant_family_id or p.family_name for p in members):
                reason='Already linked or requires manual family review'
            row={'family':label,'status':'REVIEW' if reason else 'READY','reason':reason,
                 'products':[{'handle':p.slug,'reference':'https://suryavets.com/products/'+p.slug,
                              'packs':[{'id':v.pk,'size':v.name,'sku':v.sku,'price':str(v.current_price)} for v in p.variants.all()]} for p in members]}
            if options['apply'] and not reason:
                packs.sort(key=lambda item:item[2][0]/(1000 if item[2][1] in ('g','ml') else 1))
                root=packs[0][0]; now=timezone.now()
                Product.objects.filter(pk=root.pk).update(family_name=label,updated_at=now)
                root.collections.add(*{c.pk for p in members for c in p.collections.all()})
                root.pet_categories.add(*{c.pk for p in members for c in p.pet_categories.all()})
                for index,(product,pack,(quantity,unit)) in enumerate(packs):
                    if product.pk!=root.pk:
                        Product.objects.filter(pk=product.pk).update(variant_family=root,updated_at=now)
                    values={'quantity':quantity,'unit':unit,'display_order':index,'updated_at':now}
                    # Same exact source stem/name/brand establishes size family; no best-value claims
                    # until formulation comparisons are explicitly reviewed by staff.
                    if not pack.image_id:
                        photo=next(iter(product.images.all()),None)
                        if photo: values['image']=photo
                    ProductVariant.objects.filter(pk=pack.pk).update(**values)
                CRMActivity.objects.create(kind='note',text=f'Catalog [{root.pk}] Linked existing Shopify packs: {label}. Source handles: '+', '.join(p.slug for p in members)+'. No product IDs, prices, variants, order snapshots or ledger ownership were moved.')
                row.update(status='LINKED',canonical=root.slug); applied+=1
            records.append(row)
        path=Path(options['report']); path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
        self.stdout.write(f'Candidate families={len(records)}, ready={sum(r["status"]=="READY" for r in records)}, linked={applied}, review={sum(r["status"]=="REVIEW" for r in records)}')
