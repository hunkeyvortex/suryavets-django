"""Copy existing field-owned media only; never infer product/image relationships."""
import hashlib
import json
from pathlib import Path, PurePosixPath

from django.apps import apps
from django.conf import settings
from django.core.files import File
from django.core.files.storage import storages
from django.core.management.base import BaseCommand, CommandError
from django.db.models import FileField


BACKEND = 'cloudinary_storage.storage.MediaCloudinaryStorage'
PREFIX = 'svm/'  # Leave room for media/products/thumbnails/ in 100-character fields.


def media_references():
    for model in apps.get_models():
        for field in model._meta.concrete_fields:
            if isinstance(field, FileField):
                # A default manager may hide archived/inactive rows. They still
                # own media that must remain available if staff restore them.
                for pk, name in model._base_manager.exclude(**{field.name: ''}).exclude(
                        **{field.name: None}).values_list('pk', field.name).iterator():
                    yield model, field, pk, str(name)


def local_path(root, name):
    # Reject paths that could escape the owner's selected media directory.
    if '\\' in name or ':' in name or PurePosixPath(name).is_absolute():
        raise ValueError('Unsafe or external field path')
    path = (root / name).resolve()
    if not path.is_relative_to(root):
        raise ValueError('Field path escapes media root')
    return path


def target_name(name, path):
    digest = hashlib.sha256(name.encode())
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    # The hash includes the original name AND bytes; unrelated files never collide.
    folder = PurePosixPath(name).parent.as_posix()
    return PREFIX + (folder + '/' if folder != '.' else '') + digest.hexdigest()


def migration_storage():
    from cloudinary_storage.storage import MediaCloudinaryStorage
    import cloudinary.uploader

    class DeterministicStorage(MediaCloudinaryStorage):
        def _upload(self, name, content):
            return cloudinary.uploader.upload(
                content, public_id=name, resource_type=self._get_resource_type(name),
                overwrite=False, unique_filename=False, tags=self.TAG,
            )
    return DeterministicStorage()


class Command(BaseCommand):
    help = 'Migrate existing local media to Cloudinary; run --dry-run first. No source URLs are edited.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--media-root', help='Original local media folder (defaults to MEDIA_ROOT).')

    def handle(self, *args, **options):
        dry = options['dry_run']
        cloud = settings.STORAGES['default']['BACKEND'] == BACKEND
        if not dry and not cloud:
            raise CommandError('Select the Cloudinary media backend before applying.')
        root = Path(options['media_root'] or settings.MEDIA_ROOT).resolve()
        if not root.is_dir():
            raise CommandError('Local media root must be an existing directory.')
        storage = storages['default'] if cloud else None
        uploader = migration_storage() if cloud and not dry else None
        counts = dict(total_references=0, local_found=0, already_cloud_hosted=0,
                      missing_local=0, would_upload=0, uploaded=0, updated_references=0, errors=0)
        seen = {}
        for model, field, pk, name in media_references():
            counts['total_references'] += 1
            label = f'{model._meta.label}:{pk}:{field.name}'
            try:
                path = local_path(root, name)
                found = path.is_file()
                counts['local_found'] += int(found)
                if name not in seen:
                    if storage and storage.exists(name):
                        seen[name] = ('hosted', name)
                    elif not found:
                        seen[name] = ('missing', name)
                    else:
                        if path.stat().st_size == 0:
                            raise ValueError('Empty local file')
                        target = target_name(name, path)
                        # The adapter defaults to a 'media/' prefix. Include it
                        # before upload so the saved name and retry lookup agree.
                        target = storage._prepend_prefix(target) if storage else 'media/' + target
                        if field.max_length and len(target) > field.max_length:
                            raise ValueError('Target name exceeds existing field length')
                        remote = bool(storage and storage.exists(target))
                        if not remote:
                            counts['would_upload'] += 1
                            if not dry:
                                with path.open('rb') as stream:
                                    saved = uploader.save(target, File(stream))
                                if saved != target:
                                    raise ValueError('Unexpected remote name; database unchanged')
                                counts['uploaded'] += 1
                        seen[name] = ('mapped', target)
                state, target = seen[name]
                if state == 'hosted':
                    counts['already_cloud_hosted'] += 1
                elif state == 'missing':
                    counts['missing_local'] += 1
                    self.stdout.write(f'MISSING {label} {name}')
                elif not dry:
                    # Compare-and-set: never overwrite a concurrent staff edit.
                    changed = model._base_manager.filter(pk=pk, **{field.name: name}).update(**{field.name: target})
                    if not changed:
                        raise ValueError('Reference changed concurrently; rerun to reconcile')
                    counts['updated_references'] += changed
                    self.stdout.write(f'MAPPED {label} {name} -> {target}')
            except Exception as error:
                counts['errors'] += 1
                # Provider exception text can contain credentials/request URLs.
                self.stderr.write(f'ERROR {label}: {type(error).__name__}; reference not reassigned')
        self.stdout.write(json.dumps({'dry_run': dry, 'remote_checked': cloud, **counts}, sort_keys=True))
        if counts['errors']:
            raise CommandError('Media migration had errors; inspect the record IDs above and retry safely.')
