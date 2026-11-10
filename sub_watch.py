# Следит за подпиской собеседников демо-бота @TerentievSuperProdazhi_bot
# на канал @upsales_school. Когда человек, который раньше писал боту,
# подписывается на канал, бот автоматически пишет ему
# «Спасибо, (Имя), за подписку, продолжаем».
# Состояние хранится в sub_state.json и коммитится обратно в репозиторий.
import json
import os
import urllib.request
import urllib.parse
import datetime

NOYA_KEY = os.environ['NOYA_KEY']
TG_TOKEN = os.environ['DEMO_BOT_TOKEN']
CHANNEL_ID = '1bf8b87d-8dac-41b4-ae77-6dea82272a7a'  # демо-бот в Ное
TG_CHAT = '@upsales_school'
STATE_FILE = 'sub_state.json'


def http_json(url, headers=None, body=None):
    req = urllib.request.Request(url, headers=headers or {})
    data = None
    if body is not None:
        data = json.dumps(body).encode('utf-8')
        req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, data=data, timeout=30) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        return {'ok': False, 'error': str(e)}


def check_subscribed(user_id):
    url = ('https://api.telegram.org/bot%s/getChatMember?chat_id=%s&user_id=%s'
           % (TG_TOKEN, urllib.parse.quote(TG_CHAT), user_id))
    res = http_json(url)
    if not res.get('ok') or 'result' not in res:
        return None  # неизвестно (ошибка API или пользователь не найден)
    return res['result'].get('status') in ('member', 'administrator', 'creator')


def main():
    try:
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            state = json.load(f)
    except Exception:
        state = {}
    meta = state.setdefault('_meta', {'totalSent': 0})

    dialogs = http_json('https://noya-ai.ru/api/dialogs',
                        headers={'Authorization': 'Bearer ' + NOYA_KEY})
    if not isinstance(dialogs, list):
        raise RuntimeError('Не удалось получить диалоги из Нои: %s' % str(dialogs)[:200])
    demo = [d for d in dialogs if d.get('channel_id') == CHANNEL_ID]

    sent = 0
    checked = 0
    pending = 0
    for d in demo:
        uid = str(d.get('contact_id') or '')
        if not uid:
            continue
        name = ((d.get('contact_name') or '').strip().split() or ['друг'])[0]
        sub = check_subscribed(uid)
        if sub is None:
            continue
        checked += 1
        rec = state.get(uid)
        if rec is None:
            # Первый раз видим контакт: только запоминаем, никому не пишем.
            state[uid] = {'name': name, 'subscribed': sub, 'thanked': sub}
            print(uid, name, '- новый контакт, подписан:', sub)
        else:
            rec['name'] = name
            if not rec.get('subscribed') and sub and not rec.get('thanked'):
                text = 'Спасибо, %s, за подписку, продолжаем' % name
                res = http_json('https://api.telegram.org/bot%s/sendMessage' % TG_TOKEN,
                                body={'chat_id': uid, 'text': text})
                if res.get('ok'):
                    rec['thanked'] = True
                    rec['subscribed'] = True
                    sent += 1
                    meta['totalSent'] += 1
                    print(uid, name, '- ОТПРАВЛЕНО поздравление')
                else:
                    print(uid, name, '- ошибка отправки:', str(res)[:150])
            else:
                rec['subscribed'] = sub
        if not state.get(uid, {}).get('subscribed'):
            pending += 1

    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=1)

    print('Готово. Диалогов: %d, проверено: %d, ждут подписки: %d, '
          'отправлено сейчас: %d (всего: %d) at %s'
          % (len(demo), checked, pending, sent, meta['totalSent'],
             datetime.datetime.utcnow().isoformat(timespec='seconds')))


if __name__ == '__main__':
    main()
