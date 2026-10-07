"""Source text cards plus actual original images."""

from len_bot.text_cards import CardSection
from .models import Dynamic, Fanart, Media


def media_text(items: list[Media]) -> str:
    rows = []
    for item in items:
        details = [item.kind]
        for key, value in item.model_dump(exclude_none=True).items():
            if key != 'kind':
                details.append(f'{key}: {value}')
        rows.append('\n'.join(details))
    return '\n\n'.join(rows)


def dynamic_sections(item: Dynamic) -> tuple[str, str, list[CardSection], list[str]]:
    title = f'{item.member.name} · 动态'
    subtitle = (f'动态 {item.dynamicId}\n{item.publishedAt or ""} · {item.type}\n'
                f'点赞 {item.likeCount} / 评论 {item.commentCount} / 转发 {item.forwardCount}')
    sections = [CardSection('', item.contentText)]
    if item.media:
        sections.append(CardSection('媒体信息', media_text(item.media)))
    urls = list(item.images)
    if item.orig is not None:
        original = item.orig
        sections.append(CardSection(f'转发原文 · {original.authorName}', original.text))
        metadata = []
        for key in ('dynamicId', 'authorMid', 'publishedAt', 'type', 'url'):
            value = getattr(original, key)
            if value is not None:
                metadata.append(f'{key}: {value}')
        if metadata:
            sections.append(CardSection('原文信息', '\n'.join(metadata)))
        if original.media:
            sections.append(CardSection('原文媒体信息', media_text(original.media)))
        urls.extend(original.images)
    # The same source URL can appear in both the repost and original's image list.
    return title, subtitle, sections, list(dict.fromkeys(urls))


def fanart_sections(item: Fanart) -> tuple[str, str, list[CardSection], list[str]]:
    title = f'{item.authorName} · {"二创" if item.kind == "fanart" else "物料"}'
    subtitle = f'{item.sourceDynamicId}\n{item.category} / {item.contentType} / {", ".join(item.characterTags)}'
    sections = [CardSection('', item.text)]
    metrics = []
    if item.viewCount is not None:
        metrics.append(f'播放 {item.viewCount}')
    if item.favoriteCount is not None:
        metrics.append(f'收藏 {item.favoriteCount}')
    if item.statsFetchedAt is not None:
        metrics.append('统计于 ' + item.statsFetchedAt)
    if metrics:
        sections.append(CardSection('数据', '\n'.join(metrics)))
    if item.mediaUrl:
        sections.append(CardSection('媒体链接', item.mediaUrl))
    sections.append(CardSection('作者', f'{item.authorName} / UID {item.authorUid}\n{item.authorSpaceUrl}'))
    return title, subtitle, sections, list(dict.fromkeys(item.images))
