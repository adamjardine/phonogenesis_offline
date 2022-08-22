import logging

from flask import jsonify, request, session, abort
from sqlalchemy.exc import IntegrityError

from app import app, DEFAULT_DATA, db, get_formatted_timestr
from app.models import User, Message, Group, UserGroup, Quiz, UserQuiz, QuizQuestion, Attempt, Question
from script import *
from script.morphology import ParadigmGenerator

LOGGER = logging.getLogger("app.logger")
ACCOUNT_TYPES = ['student', 'professor', 'admin']
registered_ip = {}
SAME_IP_REGISTER_LIMIT = 1
SIMPLE_QUESTION_MAX_SIZE = 50


@app.route('/env', methods=['GET'])
def environment_data():
    return jsonify(env=DEFAULT_DATA)


@app.route('/user/login', methods=['POST'])
def login():
    if 'userid' in session:
        return jsonify(result=User.query.get(session['userid']))

    username = request.json['username']
    password = request.json['password']
    user = User.query.filter_by(username=username).first()
    if user is None or not user.check_password(password):
        return jsonify(result=None)
    session['userid'] = user.id
    return jsonify(result=user)


def _validate_session():
    if 'userid' in session and session['userid']:
        session_user = User.query.get(session['userid'])
        if session_user:
            return session_user
    return None


@app.route('/user/logout', methods=['GET'])
def logout():
    session.pop('userid', None)
    return jsonify()


@app.route('/user/check-session', methods=['GET'])
def check_session():
    session_user = _validate_session()
    if session_user:
        return jsonify(currentUser=session_user)
    else:
        return jsonify(currentUser=None)


@app.route('/users', methods=['GET'])
def get_users():
    if not _validate_session():
        abort(401)
    return jsonify(User.query.all())


@app.route('/user/<username>', methods=['DELETE'])
def delete_user(username):
    session_user = _validate_session()
    if not session_user or session_user.type != 'admin':
        abort(401)

    target_user = User.query.filter_by(username=username).first()
    if target_user:
        db.session.delete(target_user)
        db.session.commit()
        return jsonify(success=True)
    else:
        return jsonify(success=False, message='No user with username {} found'.format(username))


@app.route('/user', methods=['POST'])
def create_user():
    session_user = _validate_session()
    curr_ip = str(request.remote_addr)
    if not session_user:
        if curr_ip in registered_ip:
            if registered_ip[curr_ip] >= SAME_IP_REGISTER_LIMIT:
                return jsonify(success=False,
                               message='You have created more than {} accounts from your current IP. Please contact '
                                       'an admin to register the account for you.'.format(SAME_IP_REGISTER_LIMIT))
        else:
            registered_ip[curr_ip] = 0

    data = request.json
    if 'name' not in data or 'type' not in data or 'email' not in data or \
            'username' not in data or 'password' not in data:
        abort(400)

    name = data['name']
    type_ = data['type']
    email = data['email']
    username = data['username']
    password = data['password']

    if type_ not in ACCOUNT_TYPES:
        abort(400)
    if type_ != 'student' and (not session_user or session['userid']['type'] != 'admin'):
        return jsonify(success=False,
                       message='You do not have permission to create an account of this type. Please contact admin to '
                               'create an account for you.')

    new_user = User(name=name, type=type_, email=email, username=username)
    new_user.set_password(password)

    try:
        db.session.add(new_user)
        db.session.commit()
        if not session_user:
            registered_ip[curr_ip] += 1
        return jsonify(success=True)
    except IntegrityError:
        return jsonify(success=False, message='User creation failed(username unique? non-empty password?)')


@app.route('/message/<msgid>', methods=['DELETE'])
def delete_message(msgid):
    session_user = _validate_session()
    if not session_user:
        abort(401)

    try:
        message_id = int(msgid)
    except ValueError:
        return jsonify(success=False, message='Message id must be an integer!')
    target_message = Message.query.get(int(message_id))

    if not target_message:
        return jsonify(success=False, message='Message with id {} does not exist.'.format(msgid))

    if session_user.type != 'admin' and target_message.from_user_id != session['user']['id'] and \
            target_message.to_user_id != session_user.id:
        abort(401)

    db.session.delete(target_message)
    db.session.commit()
    return jsonify(success=True)


@app.route('/message/<username>', methods=['POST'])
def send_message(username):
    session_user = _validate_session()
    if not session_user:
        abort(401)
    if 'message' not in request.json:
        abort(400)

    target_user = User.query.filter_by(username=username).first()

    if not target_user:
        return jsonify(success=False, message="Target user {} does not exist.".format(username))

    message = Message(content=request.json['message'], from_user_id=session_user.id, to_user_id=target_user.id,
                      timestamp=get_formatted_timestr())
    db.session.add(message)
    db.session.commit()
    return jsonify(success=True)


@app.route('/groups', methods=['GET'])
def get_groups():
    if not _validate_session():
        abort(401)
    return jsonify(Group.query.all())


@app.route('/group/user', methods=['PATCH'])
def remove_from_group():
    session_user = _validate_session()
    if not session_user:
        abort(401)
    if 'userid' not in request.json or 'groupid' not in request.json:
        abort(400)
    if request.json['userid'] != session_user.id and session_user.id == 'student':
        abort(401)
    try:
        user_id = int(request.json['userid'])
        group_id = int(request.json['groupid'])
    except ValueError:
        abort(400)
        return
    target_links = UserGroup.query.filter_by(user_id=user_id, group_id=group_id).all()
    if not target_links or len(target_links) == 0:
        return jsonify(success=False,
                       message="User {} is not in group {} or they do not exist.".format(user_id, group_id))
    for link in target_links:
        db.session.delete(link)
    db.session.commit()
    return jsonify(success=True)


@app.route('/group/user', methods=['POST'])
def add_to_group():
    session_user = _validate_session()
    if not session_user or session_user.type == 'student':
        abort(401)
    if 'username' not in request.json or 'groupid' not in request.json:
        abort(400)
    try:
        group_id = int(request.json['groupid'])
    except ValueError:
        abort(400)
        return
    target_user = User.query.filter_by(username=request.json['username']).first()
    if not target_user:
        return jsonify(success=False, message="User {} does not exist!".format(request.json['username']))
    if UserGroup.query.filter_by(user_id=target_user.id, group_id=group_id).first():
        return jsonify(success=False, message="User {} already enrolled in the group!".format(request.json['username']))
    new_link = UserGroup(user_id=target_user.id, group_id=group_id)
    db.session.add(new_link)
    db.session.commit()
    return jsonify(success=True)


@app.route('/group', methods=['POST'])
def create_group():
    session_user = _validate_session()
    if not session_user or session_user.type == 'student':
        abort(401)
    if 'ownerid' not in request.json or 'name' not in request.json:
        abort(400)
    try:
        owner_id = int(request.json['ownerid'])
    except ValueError:
        abort(400)
        return
    new_group = Group(name=request.json['name'], owner_id=owner_id)

    try:
        db.session.add(new_group)
        db.session.commit()
        return jsonify(success=True)
    except IntegrityError:
        return jsonify(success=False, message="Group registration failed! (is group name unique?)")


@app.route('/group/<groupid>', methods=['DELETE'])
def delete_group(groupid):
    session_user = _validate_session()
    if not session_user or session_user.type == 'student':
        abort(401)
    try:
        group_id = int(groupid)
    except ValueError:
        abort(400)
        return

    target_group = Group.query.get(group_id)
    previous_members = target_group.users()
    db.session.delete(target_group)
    db.session.commit()
    return jsonify(success=True, students=previous_members)


@app.route('/user', methods=['PATCH'])
def edit_user():
    session_user = _validate_session()
    if not session_user or session_user.type != 'admin':
        abort(401)
    data = request.json
    if 'username' not in data or 'password' not in data or 'email' not in data or 'name' not in data:
        abort(400)
    username = data['username']
    name = data['name']
    email = data['email']
    password = data['password']

    target_user = User.query.filter_by(username=username).first()

    if not target_user:
        return jsonify(success=False, message="User {} does not exist!".format(username))

    target_user.name = name
    target_user.email = email

    if len(password) > 0:
        target_user.set_password(password)

    try:
        db.session.commit()
        return jsonify(success=True)
    except IntegrityError:
        return jsonify(success=False, message="Update failed!")


@app.route('/group/message', methods=['POST'])
def broadcast_group_message():
    session_user = _validate_session()
    if not session_user:
        abort(401)

    if 'groupName' not in request.json or 'message' not in request.json:
        abort(400)

    group_name = request.json['groupName']
    message = request.json['message']

    target_group = Group.query.filter_by(name=group_name).first()

    if not target_group:
        return jsonify(success=False, message="Group {} does not exist.".format(group_name))

    messages = []
    curr_userid = session_user.id
    timestamp = get_formatted_timestr()
    if curr_userid != target_group.owner_id:
        messages.append(
            Message(content=message, from_user_id=curr_userid, to_user_id=target_group.owner_id, timestamp=timestamp))
    for user in target_group.users():
        if user.id != curr_userid:
            messages.append(Message(content=message, from_user_id=curr_userid, to_user_id=user.id, timestamp=timestamp))

    try:
        for msg in messages:
            db.session.add(msg)
        db.session.commit()
        return jsonify(success=True)
    except IntegrityError:
        return jsonify(success=False, message="Broadcast failed!")


@app.route('/rules', methods=['GET'])
def get_rules():
    return jsonify(rules=DEFAULT_DATA['rules'])


@app.route('/quiz/register', methods=['POST'])
def register_quiz_result():
    if not _validate_session():
        abort(401)

    data = request.json
    if 'userid' not in data or 'quizid' not in data or 'result' not in data or \
            'score' not in data['result'] or 'answers' not in data['result']:
        abort(400)
    try:
        user_id = int(data['userid'])
        quiz_id = int(data['quizid'])
    except ValueError:
        abort(400)
        return

    attempt = Attempt(score=data['result']['score'], answers=data['result']['answers'], user_id=user_id,
                      quiz_id=quiz_id, timestamp=get_formatted_timestr())
    try:
        db.session.add(attempt)
        db.session.commit()
        return jsonify(success=True)
    except IntegrityError:
        return jsonify(success=False, message="Quiz result registration failed!")


@app.route('/makequiz', methods=['POST'])
def create_quiz():
    if not _validate_session():
        abort(401)

    data = request.json
    if 'timeLim' not in data or 'name' not in data or 'ownerid' not in data or 'groupName' not in data or \
            'questions' not in data:
        abort(400)

    try:
        time_limit = int(data['timeLim'])
        ownerid = int(data['ownerid'])
        questions_attrs = list(data['questions'])
    except ValueError:
        abort(400)
        return
    name = data['name']
    group_name = data['groupName']
    target_group = Group.query.filter_by(name=group_name).first()

    if not target_group:
        return jsonify(success=False, message="Group {} does not exist!".format(group_name))

    questions = []
    for question_attr in questions_attrs:
        size = int(question_attr['size'])
        max_cadt = int(question_attr['maxCADT'])
        rule = DEFAULT_DATA['rules'][question_attr['rule']]
        phonemes = DEFAULT_DATA['phonemes']
        gen = Generator(phonemes, DEFAULT_DATA['templates'], rule, 5, DEFAULT_DATA['f2t'], DEFAULT_DATA['f2ss'])
        rule_type = rule.get_rule_type(phonemes, DEFAULT_DATA['f2t'], DEFAULT_DATA['f2ss'])

        q_data = gen.generate(GenMode.IPAg, [size, max_cadt * 5], True, False,
                              DEFAULT_DATA['gloss_grp'])

        question_obj = Question(templates=q_data['templates'], poi=' '.join(q_data['phone_interest']),
                                rule_type=str(rule_type), phonemes=' '.join(q_data['phonemes']),
                                rule_name=rule.get_name(), gloss=q_data['Gloss'], UR=q_data['UR'], SR=q_data['SR'],
                                size=size, canUR=bool(question_attr['canUR']),
                                canPhoneme=bool(question_attr['canPhoneme']), maxCADT=max_cadt,
                                rule_content=rule.get_content_str(), rule_family=rule.get_family().get_name())
        questions.append(question_obj)
        db.session.add(question_obj)

    quiz = Quiz(name=name, owner_id=ownerid, time_limit_seconds=time_limit)
    db.session.add(quiz)
    db.session.flush()

    for question in questions:
        db.session.add(QuizQuestion(quiz_id=quiz.id, question_id=question.id))

    for user_bond in target_group.users_bond:
        db.session.add(UserQuiz(quiz_id=quiz.id, user_id=user_bond.user_id))

    db.session.commit()
    return jsonify(success=True)


@app.route('/question', methods=['POST'])
def get_simple_question():
    data = request.json
    if 'shuffle' not in data or 'isIPAg' not in data or 'size' not in data or 'rule_family' not in data:
        abort(400)
    try:
        shuffle = bool(data['shuffle'])
        isIPAg = bool(data['isIPAg'])
        size = int(data['size'])
    except ValueError:
        abort(400)
        return
    rule_family = data['rule_family']
    rules = list(DEFAULT_DATA['rules'].values())
    rule: Rule
    import random

    if rule_family == "Random":
        rule = random.choice(rules)
    else:
        rule = random.choice([r for r in rules if r.get_family().get_name() == rule_family])

    if isIPAg:
        gen_mode = GenMode.IPAg
    else:
        gen_mode = GenMode.nIPAg

    phonemes = get_random_phonemes([rule.get_a_matcher(None, None, DEFAULT_DATA['f2ss'])])
    rule_type = rule.get_rule_type(phonemes, DEFAULT_DATA['f2t'], DEFAULT_DATA['f2ss'])
    gen = Generator(phonemes, DEFAULT_DATA['templates'], rule, 5, DEFAULT_DATA['f2t'], DEFAULT_DATA['f2ss'])
    try:
        q_data = gen.generate(gen_mode, [size, SIMPLE_QUESTION_MAX_SIZE - size], True, shuffle,
                              DEFAULT_DATA['gloss_grp'])
    except GeneratorError or ValueError:
        return jsonify(success=False, message="Sorry! Failed to get a question. Please try again.")

    simple_question = {'templates': q_data['templates'], 'poi': ' '.join(q_data['phone_interest']),
                       'rule_type': str(rule_type), 'phonemes': ' '.join(q_data['phonemes']),
                       'rule_name': rule.get_name(), 'gloss': q_data['Gloss'], 'UR': q_data['UR'], 'SR': q_data['SR'],
                       'size': size, 'canUR': True, 'canPhoneme': True, 'maxCADT': 100, 'qType': 'Simple',
                       'rule_content': rule.get_content_str(), 'rule_family': rule.get_family().get_name()}
    # curr_obj = {'phonemes': q_data['phonemes'], 'rule': rule}
    # cache.set("curr_info", curr_obj)
    return jsonify(success=True, question=simple_question)


def supported_rule_families_name(default_rules):
    morph_rule_dic = {}
    edge_rules = [r for r in default_rules if r._Cs_edge == [False] and r._Ds_edge == [False]]
    for rule in edge_rules:
        if rule.get_family() not in morph_rule_dic:
            morph_rule_dic[rule.get_family()] = 1
        else:
            morph_rule_dic[rule.get_family()] += 1
    return [fam.get_name() for fam in morph_rule_dic.keys()]


@app.route('/rule/families', methods=['GET'])
def get_rule_families():
    rules = list(DEFAULT_DATA['rules'].values())
    return jsonify(dist_families=[fam.get_name() for fam in DEFAULT_DATA['rule_fam']],
                   morph_families=supported_rule_families_name(rules))


@app.route('/morphology/question', methods=['POST'])
def get_morphology_question():
    data = request.json
    if 'shuffle' not in data or 'isIPAg' not in data or 'rule_family' not in data:
        abort(400)
    try:
        shuffle = bool(data['shuffle'])
        isIPAg = bool(data['isIPAg'])
    except ValueError:
        abort(400)
        return

    q_data = None
    rule_type = None
    reset_limit = 10
    try_count = 0
    rule_family = data['rule_family']
    rules = list(DEFAULT_DATA['rules'].values())
    # TODO: Temporarily ignoring all rules that involves edge environments
    rules = [r for r in rules if r._Cs_edge == [False] and r._Ds_edge == [False]]

    import random
    if rule_family == "Random":
        rule_family = random.choice(supported_rule_families_name(rules))
        print(rule_family)
        # rule = random.choice(rules)
    rule = random.choice([r for r in rules if r.get_family().get_name() == rule_family])

    while try_count < reset_limit:
        q_data = None
        while True:
            try:
                phonemes = get_random_phonemes([rule.get_a_matcher(None, None, DEFAULT_DATA['f2ss'])])
                rule_type = rule.get_rule_type(phonemes, DEFAULT_DATA['f2t'], DEFAULT_DATA['f2ss'])
                p_gen = ParadigmGenerator(rule, phonemes, DEFAULT_DATA['templates'], DEFAULT_DATA['f2t'],
                                          DEFAULT_DATA['f2ss'])
                q_data = p_gen.get_paradigm_question(shuffle, isIPAg, DEFAULT_DATA['f2t'], DEFAULT_DATA['f2ss'],
                                                     affix_type=random.choice(["PREFIX", "SUFFIX"]))
            except IndexError as e:
                try_count += 1
                LOGGER.error(e)
                pass
            if q_data is None:
                try_count += 1
                pass
            else:
                break
        if q_data is not None:
            break

    if q_data:
        morphology_question = {'qType': "Morphology", 'templates': q_data['templates'],
                               'poi': q_data['poi'], 'rule_type': str(rule_type),
                               'phonemes': ' '.join(q_data['phonemes']),
                               'rule_name': rule.get_name(), 'gloss': q_data['Gloss'], 'UR': q_data['ur_words'],
                               'core_data': q_data['core_data'], 'canUR': True, 'canPhoneme': True,
                               'rule_content': rule.get_content_str(), 'rule_family': rule.get_family().get_name(),
                               'header_row': q_data['header_row'], 'trans_patterns': q_data['trans_patterns']}

        return jsonify(success=True, question=morphology_question)
    else:
        return jsonify(success=False, message="Sorry! Failed to get a question. Please try again.")


@app.route('/testbox', methods=['POST'])
def test_UR():
    data = request.json
    ur = data["UR"].replace(" ", "")
    phoneme_list = data["phonemes"].split(" ")
    phonemes = [Word(phoneme.replace("ɡ", "g")) for phoneme in phoneme_list]
    curr_rule = DEFAULT_DATA["rules"][data["rule_name"]]
    sr = curr_rule.apply(Word(ur), phonemes, DEFAULT_DATA['f2t'], DEFAULT_DATA['f2ss'])[0]
    return jsonify(success=True, sr=sr)
