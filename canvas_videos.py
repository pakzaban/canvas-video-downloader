#!/usr/bin/env python3
"""Download Panopto videos using their visible Download button in Canvas."""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

START = 'https://canvas.upenn.edu/courses/1942808/pages/%3E-distributed-gpu-computation-introduction-9-39?module_item_id=37455251'


def safe_name(text):
    return re.sub(r'[^\w. -]', '_', text).strip(' .')[:140] or 'video'


def valid_url(url):
    p = urlsplit(url)
    return (p.scheme == 'https' and p.netloc == 'canvas.upenn.edu'
            and p.path.startswith('/courses/1942808/') and not p.fragment)


async def download_button(page, wait_seconds):
    deadline = asyncio.get_running_loop().time() + wait_seconds
    while asyncio.get_running_loop().time() < deadline:
        for frame in page.frames:
            if urlsplit(frame.url).hostname != 'upenn.hosted.panopto.com':
                continue
            button = frame.get_by_role('button', name='Download', exact=True)
            try:
                if await button.count() == 1 and await button.is_visible() and await button.is_enabled():
                    return button
            except Exception:
                pass  # A frame may detach while the Canvas LTI tool loads.
        await asyncio.sleep(0.5)
    return None


async def run(args):
    from playwright.async_api import async_playwright
    args.out.mkdir(parents=True, exist_ok=True)
    manifest_path = args.out / 'completed.json'
    completed = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()
        try:
            await page.goto(args.start, wait_until='domcontentloaded')
            await asyncio.to_thread(input, '\nSign in to Penn in the opened browser. Wait until the lesson video appears, then press Enter here: ')
            if not valid_url(page.url):
                raise RuntimeError('The browser is not on the course lesson yet. Sign in and rerun.')
            if await download_button(page, args.wait) is None:
                raise RuntimeError('No enabled Panopto Download button on the starting lesson.')
            urls = []
            if args.urls:
                urls = [line.strip() for line in args.urls.read_text().splitlines()
                        if line.strip() and not line.lstrip().startswith('#')]
                if not urls or any(not valid_url(url) for url in urls):
                    raise RuntimeError('The URL list must contain lesson URLs from this Penn Canvas course.')
            else:
                # Follow Canvas navigation, which may include readings or quizzes.
                seen = set()
                for index in range(args.count):
                    current = page.url
                    if not valid_url(current) or current in seen:
                        break
                    seen.add(current)
                    urls.append(current)
                    print(f'Queued {index + 1}: {await page.title()}', flush=True)
                    if index + 1 == args.count:
                        break
                    next_link = page.get_by_role('link', name='Next Module Item', exact=True)
                    try:
                        await next_link.wait_for(state='visible', timeout=10000)
                    except Exception:
                        break
                    href = await next_link.get_attribute('href')
                    from urllib.parse import urljoin
                    target = urljoin(page.url, href or '')
                    if not href or not valid_url(target):
                        break
                    await page.goto(target, wait_until='domcontentloaded')
            urls = list(dict.fromkeys(urls))
            print(f'Batch: {len(urls)} course items; {args.workers} concurrent downloads.')
            if args.dry_run:
                for url in urls:
                    print(url)
                return 0
            semaphore = asyncio.Semaphore(args.workers)

            async def one(url):
                async with semaphore:
                    key = hashlib.sha256(url.encode()).hexdigest()[:16]
                    previous = completed.get(key)
                    if previous and (args.out / Path(previous).name).is_file() and not args.overwrite:
                        print(f'EXISTS: {previous}', flush=True)
                        return 'exists'
                    worker = await context.new_page()
                    temporary = None
                    label = key
                    try:
                        await worker.goto(url, wait_until='domcontentloaded', timeout=60000)
                        label = await worker.title()
                        button = await download_button(worker, args.wait)
                        if button is None:
                            print(f'SKIPPED: {label} — no enabled Panopto Download button found.', flush=True)
                            return 'skipped'
                        async with worker.expect_download(timeout=60000) as event:
                            await button.click()
                        download = await event.value
                        filename = f'{key}_{safe_name(download.suggested_filename)}'
                        destination = args.out / filename
                        temporary = destination.with_suffix(destination.suffix + '.part')
                        await asyncio.wait_for(download.save_as(str(temporary)), args.timeout)
                        temporary.replace(destination)
                        completed[key] = filename
                        # Synchronous, atomic update within this event loop.
                        manifest_tmp = manifest_path.with_suffix('.json.part')
                        manifest_tmp.write_text(json.dumps(completed, indent=2))
                        manifest_tmp.replace(manifest_path)
                        print(f'SAVED: {filename}', flush=True)
                        return 'saved'
                    except Exception as error:
                        # Exception strings can contain signed media URLs; do not print them.
                        print(f'FAILED: {label} ({type(error).__name__}); rerun to retry.', flush=True)
                        return 'failed'
                    finally:
                        if temporary and temporary.exists():
                            temporary.unlink()
                        await worker.close()

            results = await asyncio.gather(*(one(url) for url in urls))
            print(', '.join(f'{name}: {results.count(name)}' for name in ('saved', 'exists', 'skipped', 'failed')))
            print(f'Output: {args.out.resolve()}')
            return int('failed' in results)
        finally:
            await context.close()
            await browser.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--start', default=START)
    parser.add_argument('--count', type=int, default=5, help='Number of consecutive course items, including starting lesson (default 5)')
    parser.add_argument('--urls', type=Path, help='Optional text file of selected lesson URLs, one per line; replaces --count')
    parser.add_argument('--workers', type=int, default=3)
    parser.add_argument('--out', type=Path, default=Path('canvas_videos'))
    parser.add_argument('--wait', type=int, default=20, help='Seconds to wait for each video player')
    parser.add_argument('--timeout', type=int, default=1800, help='Seconds allowed per file download')
    parser.add_argument('--dry-run', action='store_true', help='List the batch without downloading')
    parser.add_argument('--overwrite', action='store_true')
    args = parser.parse_args()
    if not valid_url(args.start):
        parser.error('--start must be a lesson URL in Penn Canvas course 1942808')
    if not 1 <= args.count <= 200 or not 1 <= args.workers <= 6 or args.wait < 1 or args.timeout < 1:
        parser.error('Use count 1–200, workers 1–6, and positive wait/timeout values')
    try:
        return asyncio.run(run(args))
    except KeyboardInterrupt:
        return 130
    except RuntimeError as error:
        print(f'Error: {error}')
        return 1
    except Exception as error:
        print(f'Error: {type(error).__name__}. Check installation and network access.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
