from sqlalchemy import UniqueConstraint

from app import db
from werkzeug.security import generate_password_hash, check_password_hash

from serializable import Serializable

SERIALIZE_RECUR_LIMIT = 5


class Message(db.Model, Serializable):
    __tablename__ = 'message'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(256))
    timestamp = db.Column(db.String(64), index=True, nullable=False)
    from_user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'))
    to_user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'))

    from_user = db.relationship("User", back_populates='sent_messages', foreign_keys=[from_user_id])
    to_user = db.relationship("User", back_populates='recv_messages', foreign_keys=[to_user_id])

    def serialize(self, **kwargs):
        serialized = {'id': self.id, 'content': self.content, 'timestamp': str(self.timestamp),
                      'from_user_id': self.from_user_id, 'to_user_id': self.to_user_id}
        if 'recur' in kwargs and kwargs['recur'] < SERIALIZE_RECUR_LIMIT:
            next_recur = kwargs['recur'] + 1
            serialized['from_user'] = self.from_user.serialize(recur=next_recur)
            serialized['to_user'] = self.to_user.serialize(recur=next_recur)
        # else:
        #     serialized['from_user'] = self.from_user.username
        #     serialized['to_user'] = self.to_user.username
        return serialized

    def __repr__(self):
        return '<Message({}) from {} to {}: {}>'.format(self.id, self.from_user_id, self.to_user_id, self.content)


class Group(db.Model, Serializable):
    __tablename__ = 'group'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), unique=True, index=True, nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)

    owner = db.relationship("User", back_populates="owned_groups", foreign_keys=[owner_id])
    users_bond = db.relationship('UserGroup', back_populates="group", cascade="all, delete")

    def users(self) -> list:
        return [bond.user for bond in self.users_bond]

    def serialize(self, **kwargs):
        serialized = {'id': self.id, 'name': self.name, 'owner_id': self.owner_id}
        if 'recur' in kwargs and kwargs['recur'] < SERIALIZE_RECUR_LIMIT:
            next_recur = kwargs['recur'] + 1
            serialized['owner'] = self.owner.serialize(recur=next_recur)
            serialized['users'] = [bond.user.serialize(recur=next_recur) for bond in self.users_bond]
        # else:
        #     serialized['owner'] = self.owner.username
        #     serialized['users'] = [bond.user.username for bond in self.users_bond]
        return serialized

    def __repr__(self):
        return '<Group {} {} Owner {}>'.format(self.id, self.name, self.owner_id)


class Quiz(db.Model, Serializable):
    __tablename__ = 'quiz'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True, nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    time_limit_seconds = db.Column(db.Integer, nullable=False)

    owner = db.relationship("User", back_populates='owned_quizzes', foreign_keys=[owner_id])
    attempts = db.relationship("Attempt", back_populates='quiz', cascade="all, delete")
    questions_bond = db.relationship("QuizQuestion", back_populates='quiz', cascade="all, delete")
    targets_bond = db.relationship("UserQuiz", back_populates="quiz", cascade="all, delete")

    def serialize(self, **kwargs):
        serialized = {'id': self.id, 'name': self.name, 'owner_id': self.owner_id,
                      'time_limit_seconds': self.time_limit_seconds}
        if 'recur' in kwargs and kwargs['recur'] < SERIALIZE_RECUR_LIMIT:
            next_recur = kwargs['recur'] + 1
            serialized['owner'] = self.owner.serialize(recur=next_recur)
            serialized['attempts'] = [attempt.serialize(recur=next_recur) for attempt in self.attempts]
            serialized['questions'] = [bond.question.serialize(recur=next_recur) for bond in self.questions_bond]
            serialized['targets'] = [bond.user.serialize(recur=next_recur) for bond in self.targets_bond]
        # else:
        #     serialized['owner'] = self.owner.username
        #     serialized['attempts'] = [attempt.id for attempt in self.attempts]
        #     serialized['questions'] = [bond.question.id for bond in self.questions_bond]
        #     serialized['targets'] = [bond.user.username for bond in self.targets_bond]
        return serialized

    def __repr__(self):
        return '<Quiz {} {} Owner {} {}>'.format(self.id, self.name, self.owner_id, self.owner.username)


class UserQuiz(db.Model, Serializable):
    __tablename__ = 'userquiz'
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    __table_args__ = (UniqueConstraint('user_id', 'quiz_id', name='_user_quiz_uc'),)

    quiz = db.relationship("Quiz", back_populates="targets_bond", foreign_keys=[quiz_id])
    user = db.relationship("User", back_populates="recv_quizzes_bond", foreign_keys=[user_id])

    def serialize(self, **kwargs):
        serialized = {'id': self.id, 'quiz_id': self.quiz_id, 'user_id': self.user_id}
        if 'recur' in kwargs and kwargs['recur'] < SERIALIZE_RECUR_LIMIT:
            next_recur = kwargs['recur'] + 1
            serialized['quiz'] = self.quiz.serialize(recur=next_recur)
            serialized['user'] = self.user.serialize(recur=next_recur)
        # else:
        #     serialized['quiz'] = self.quiz.name
        #     serialized['user'] = self.user.username
        return serialized

    def __repr__(self):
        return '<Quiz {} User {}>'.format(self.quiz_id, self.user_id)


class QuizQuestion(db.Model, Serializable):
    __tablename__ = 'quizquestion'
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id', ondelete='CASCADE'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id', ondelete='CASCADE'), nullable=False)

    quiz = db.relationship("Quiz", back_populates='questions_bond', foreign_keys=[quiz_id])
    question = db.relationship("Question", back_populates='quizzes_bond', foreign_keys=[question_id])
    __table_args__ = (UniqueConstraint('quiz_id', 'question_id', name='_quiz_question_uc'),)

    def serialize(self, **kwargs):
        serialized = {'id': self.id, 'question_id': self.question_id, 'quiz_id': self.quiz_id}
        if 'recur' in kwargs and kwargs['recur'] < SERIALIZE_RECUR_LIMIT:
            next_recur = kwargs['recur'] + 1
            serialized['quiz'] = self.quiz.serialize(recur=next_recur)
            serialized['question'] = self.question.serialize(recur=next_recur)
        # else:
        #     serialized['quiz'] = self.quiz.name
        #     serialized['question'] = self.question.ruleTxt
        return serialized

    def __repr__(self):
        return '<Quiz {} Question {}>'.format(self.quiz_id, self.question_id)


class Attempt(db.Model, Serializable):
    __tablename__ = 'attempt'
    id = db.Column(db.Integer, primary_key=True)
    score = db.Column(db.PickleType, nullable=False)
    answers = db.Column(db.PickleType, nullable=False)
    timestamp = db.Column(db.String(64), index=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id', ondelete='CASCADE'), nullable=False)

    quiz = db.relationship("Quiz", back_populates="attempts", foreign_keys=[quiz_id])
    user = db.relationship("User", back_populates="quiz_attempts", foreign_keys=[user_id])

    def serialize(self, **kwargs):
        serialized = {'id': self.id, 'score': self.score, 'answers': self.answers, 'timestamp': self.timestamp,
                      'user_id': self.user_id, 'quiz_id': self.quiz_id}
        if 'recur' in kwargs and kwargs['recur'] < SERIALIZE_RECUR_LIMIT:
            next_recur = kwargs['recur'] + 1
            serialized['quiz'] = self.quiz.serialize(recur=next_recur)
            serialized['user'] = self.user.serialize(recur=next_recur)
        # else:
        #     serialized['quiz'] = self.quiz.name
        #     serialized['user'] = self.user.username
        return serialized

    def __repr__(self):
        return '<Attempt({}) User {} {} Quiz {} {} Score {}>'.format(self.id, self.user_id, self.user.username,
                                                                     self.quiz_id, self.quiz.name, self.score)


class Question(db.Model, Serializable):
    __tablename__ = 'question'
    id = db.Column(db.Integer, primary_key=True)

    templates = db.Column(db.PickleType, nullable=False)
    poi = db.Column(db.String(1024), nullable=False)
    rule_type = db.Column(db.String(32), nullable=False)
    rule_family = db.Column(db.String(128), nullable=False)
    phonemes = db.Column(db.String(1024), nullable=False)
    rule_name = db.Column(db.String(128), nullable=False)
    rule_content = db.Column(db.String(512), nullable=False)
    gloss = db.Column(db.PickleType, nullable=False)
    UR = db.Column(db.PickleType, nullable=False)
    SR = db.Column(db.PickleType, nullable=False)

    size = db.Column(db.Integer, default=20)
    canUR = db.Column(db.Boolean, default=False)
    canPhoneme = db.Column(db.Boolean, default=False)
    maxCADT = db.Column(db.Integer, default=0)

    quizzes_bond = db.relationship("QuizQuestion", back_populates='question', cascade="all, delete")

    def serialize(self, **kwargs):
        serialized = {'id': self.id, 'templates': self.templates, 'poi': self.poi, 'rule_type': self.rule_type,
                      'phonemes': self.phonemes, 'rule_name': self.rule_name, 'gloss': self.gloss,
                      'UR': self.UR, 'SR': self.SR, 'size': self.size, 'canUR': self.canUR,
                      'canPhoneme': self.canPhoneme, 'maxCADT': self.maxCADT, 'rule_content': self.rule_content}
        if 'recur' in kwargs and kwargs['recur'] < SERIALIZE_RECUR_LIMIT:
            next_recur = kwargs['recur'] + 1
            serialized['quizzes'] = [bond.quiz.serialize(recur=next_recur) for bond in self.quizzes_bond]
        # else:
        #     serialized['quizzes'] = [bond.quiz.id for bond in self.quizzes_bond]
        return serialized

    def __repr__(self):
        return '<Rule {} {}>'.format(self.id, self.rule_name)


class UserGroup(db.Model, Serializable):
    __tablename__ = 'usergroup'
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)

    group = db.relationship("Group", back_populates="users_bond", foreign_keys=[group_id])
    user = db.relationship("User", back_populates="joined_groups_bond", foreign_keys=[user_id])
    __table_args__ = (UniqueConstraint('group_id', 'user_id', name='_group_user_uc'),)

    def serialize(self, **kwargs):
        serialized = {'id': self.id, 'user_id': self.user_id, 'group_id': self.group_id}
        if 'recur' in kwargs and kwargs['recur'] < SERIALIZE_RECUR_LIMIT:
            next_recur = kwargs['recur'] + 1
            serialized['group'] = self.group.serialize(recur=next_recur)
            serialized['user'] = self.user.serialize(recur=next_recur)
        # else:
        #     serialized['group'] = self.group.name
        #     serialized['user'] = self.user.username
        return serialized

    def __repr__(self):
        return '<Group {} User {}>'.format(self.group_id, self.user_id)


class User(db.Model, Serializable):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(10), index=True, unique=False, nullable=False)
    name = db.Column(db.String(64), index=True, unique=False, nullable=False)
    email = db.Column(db.String(64), index=True, unique=False, nullable=False)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(128))

    joined_groups_bond = db.relationship('UserGroup', back_populates="user", cascade="all, delete")
    owned_groups = db.relationship('Group', back_populates="owner", cascade="all, delete")
    quiz_attempts = db.relationship('Attempt', back_populates='user', cascade="all, delete")

    recv_quizzes_bond = db.relationship('UserQuiz', back_populates='user', cascade="all, delete")
    owned_quizzes = db.relationship('Quiz', back_populates='owner', cascade="all, delete")
    recv_messages = db.relationship('Message', back_populates='to_user', cascade="all, delete",
                                    primaryjoin='and_(User.id==Message.to_user_id)')
    sent_messages = db.relationship('Message', back_populates='from_user', cascade="all, delete",
                                    primaryjoin='and_(User.id==Message.from_user_id)')

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        if len(password) == 0:
            return False
        return check_password_hash(self.password_hash, password)

    def serialize(self, **kwargs):
        serialized = {'id': self.id, 'type': self.type, 'name': self.name, 'email': self.email,
                      'username': self.username}
        if 'recur' in kwargs and kwargs['recur'] < SERIALIZE_RECUR_LIMIT:
            next_recur = kwargs['recur'] + 1
            serialized['joined_groups'] = [bond.group.serialize(recur=next_recur) for bond in self.joined_groups_bond]
            serialized['owned_groups'] = [group.serialize(recur=next_recur) for group in self.owned_groups]
            serialized['quiz_attempts'] = [attempt.serialize(recur=next_recur) for attempt in self.quiz_attempts]
            serialized['recv_quizzes'] = [bond.quiz.serialize(recur=next_recur) for bond in self.recv_quizzes_bond]
            serialized['owned_quizzes'] = [quiz.serialize(recur=next_recur) for quiz in self.owned_quizzes]
            serialized['recv_messages'] = [msg.serialize(recur=next_recur) for msg in self.recv_messages]
            serialized['sent_messages'] = [msg.serialize(recur=next_recur) for msg in self.sent_messages]
        # else:
        #     serialized['joined_groups'] = [bond.group.name for bond in self.joined_groups_bond]
        #     serialized['owned_groups'] = [group.name for group in self.owned_groups]
        #     serialized['quiz_attempts'] = [attempt.id for attempt in self.quiz_attempts]
        #     serialized['recv_quizzes'] = [bond.quiz.name for bond in self.recv_quizzes_bond]
        #     serialized['owned_quizzes'] = [quiz.name for quiz in self.owned_quizzes]
        #     serialized['recv_messages'] = [msg.content for msg in self.recv_messages]
        #     serialized['sent_messages'] = [msg.content for msg in self.sent_messages]
        return serialized

    def __repr__(self):
        return '<User {} {}>'.format(self.id, self.username)
