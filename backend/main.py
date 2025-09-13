from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, RedirectResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from uuid import uuid4
import os

app = FastAPI(title='PSK Starter API')

# --- CORS from env (fallback to permissive during development) ---
cors_env = os.environ.get("CORS_ALLOW", "*")
if cors_env == "*" or not cors_env.strip():
    allow_origins = ["*"]
else:
    allow_origins = [o.strip() for o in cors_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_methods=['*'],
    allow_headers=['*'],
)

DB = {
    'users': {},
    'events': {},
    'divisions': {},
    'regs': {},
    'teams': {},
    'matches': {},
    'submissions': {},
}

def uid():
    return uuid4().hex[:12]

class UserIn(BaseModel):
    firstName: str
    lastName: str
    email: str
    duprId: Optional[str] = None

class User(UserIn):
    id: str

class EventIn(BaseModel):
    name: str
    startDate: Optional[str] = None
    venue: Optional[str] = None

class Event(EventIn):
    id: str

class DivisionIn(BaseModel):
    eventId: str
    name: str
    type: str = Field('singles', pattern='^(singles|doubles)$')
    fixedPartner: bool = True
    target: int = 11
    winBy: int = 2
    mode: str = Field('sideout', pattern='^(sideout|rally)$')
    gamesPerMatch: int = 1

class Division(DivisionIn):
    id: str

class RegistrationIn(BaseModel):
    userId: str
    partnerUserId: Optional[str] = None

class Registration(RegistrationIn):
    id: str
    divisionId: str

class Team(BaseModel):
    id: str
    divisionId: str
    playerA: str
    playerB: Optional[str] = None

class ScoreLine(BaseModel):
    a: int
    b: int

class Submission(BaseModel):
    id: str
    matchId: str
    byTeam: str
    side: str
    scores: List[ScoreLine]
    state: str = 'pending'

class Match(BaseModel):
    id: str
    divisionId: str
    roundNo: int
    teamA: str
    teamB: str
    status: str = 'pending'
    scores: List[ScoreLine] = []
    winner: Optional[str] = None
    awaitingSubmissionId: Optional[str] = None

def get_div_teams(divId: str) -> List[Team]:
    return [t for t in DB['teams'].values() if t.divisionId == divId]

def ensure_team(divId: str, playerA: str, playerB: Optional[str]) -> str:
    for t in get_div_teams(divId):
        if t.playerA == playerA and t.playerB == playerB:
            return t.id
        if t.playerA == playerB and t.playerB == playerA:
            return t.id
    tid = uid()
    DB['teams'][tid] = Team(id=tid, divisionId=divId, playerA=playerA, playerB=playerB)
    return tid

def round_robin_ids(team_ids: List[str]) -> List[List[List[str]]]:
    teams = team_ids[:]
    if len(teams) % 2:
        teams.append('BYE')
    n = len(teams)
    half = n // 2
    rounds = []
    order = teams[:]
    for _ in range(n - 1):
        pairings = []
        for i in range(half):
            a, b = order[i], order[n-1-i]
            if 'BYE' not in (a, b):
                pairings.append([a, b])
        rounds.append(pairings)
        order = [order[0]] + [order[-1]] + order[1:-1]
    return rounds

def compute_standings(divId: str):
    table: Dict[str, Dict[str,int]] = {}
    for t in get_div_teams(divId):
        table[t.id] = {'W':0,'L':0,'PF':0,'PA':0,'PD':0}
    for m in DB['matches'].values():
        if m.divisionId != divId or m.status != 'final':
            continue
        pfA = sum(s.a for s in m.scores)
        pfB = sum(s.b for s in m.scores)
        table[m.teamA]['PF'] += pfA; table[m.teamA]['PA'] += pfB
        table[m.teamB]['PF'] += pfB; table[m.teamB]['PA'] += pfA
        if m.winner == m.teamA:
            table[m.teamA]['W'] += 1; table[m.teamB]['L'] += 1
        else:
            table[m.teamB]['W'] += 1; table[m.teamA]['L'] += 1
    for t in table.values():
        t['PD'] = t['PF'] - t['PA']
    return table

@app.get('/', include_in_schema=False)
def root():
    return {'service': 'PicoScoreKeeper API','ok': True,'health': '/health','docs': '/docs'}

@app.get('/favicon.ico', include_in_schema=False)
def favicon():
    return PlainTextResponse('', status_code=204)

@app.get('/health')
def health(): return {'ok': True}

@app.post('/users', response_model=User)
def create_user(u: UserIn):
    for existing in DB['users'].values():
        if existing.email.lower() == u.email.lower():
            raise HTTPException(409, 'Email exists')
    user = User(id=uid(), **u.model_dump())
    DB['users'][user.id] = user
    return user

@app.get('/users', response_model=List[User])
def list_users(): return list(DB['users'].values())

@app.post('/events', response_model=Event)
def create_event(e: EventIn):
    event = Event(id=uid(), **e.model_dump())
    DB['events'][event.id] = event
    return event

@app.post('/divisions', response_model=Division)
def create_division(d: DivisionIn):
    if d.eventId not in DB['events']:
        raise HTTPException(404, 'Event not found')
    div = Division(id=uid(), **d.model_dump())
    DB['divisions'][div.id] = div
    return div

@app.post('/divisions/{divId}/register', response_model=Registration)
def register(divId: str, r: RegistrationIn):
    if divId not in DB['divisions']:
        raise HTTPException(404, 'Division not found')
    if r.userId not in DB['users']:
        raise HTTPException(404, 'User not found')
    if DB['divisions'][divId].type == 'doubles' and DB['divisions'][divId].fixedPartner and not r.partnerUserId:
        raise HTTPException(400, 'partnerUserId required for fixed-partner doubles')
    reg = Registration(id=uid(), divisionId=divId, **r.model_dump())
    DB['regs'][reg.id] = reg
    if DB['divisions'][divId].type == 'singles':
        ensure_team(divId, r.userId, None)
    else:
        ensure_team(divId, r.userId, r.partnerUserId)
    return reg

@app.post('/divisions/{divId}/schedule')
def schedule_round_robin(divId: str):
    if divId not in DB['divisions']:
        raise HTTPException(404, 'Division not found')
    teams = get_div_teams(divId)
    if len(teams) < 2:
        raise HTTPException(400, 'Need at least 2 teams/players')
    team_ids = [t.id for t in teams]
    rr = round_robin_ids(team_ids)
    for mid in [mid for mid,m in DB['matches'].items() if m.divisionId == divId]:
        DB['matches'].pop(mid)
    created = []
    roundNo = 1
    for rnd in rr:
        for a,b in rnd:
            mid = uid()
            m = Match(id=mid, divisionId=divId, roundNo=roundNo, teamA=a, teamB=b)
            DB['matches'][mid] = m
            created.append(m)
        roundNo += 1
    return {'rounds': len(rr), 'matches': len(created)}

@app.get('/divisions/{divId}/matches', response_model=List[Match])
def list_matches(divId: str):
    return [m for m in DB['matches'].values() if m.divisionId == divId]

@app.post('/matches/{matchId}/submit', response_model=Submission)
def submit_score(matchId: str, payload: Dict):
    if matchId not in DB['matches']:
        raise HTTPException(404, 'Match not found')
    m: Match = DB['matches'][matchId]
    if m.status == 'final':
        raise HTTPException(400, 'Match already final')
    byTeam = payload.get('byTeam')
    side = payload.get('side')
    scores_in = payload.get('scores', [])
    if byTeam not in (m.teamA, m.teamB) or side not in ('A','B'):
        raise HTTPException(400, 'Invalid submission')
    scores = [ScoreLine(**s) for s in scores_in]
    sub = Submission(id=uid(), matchId=matchId, byTeam=byTeam, side=side, scores=scores)
    DB['submissions'][sub.id] = sub
    m.status = 'awaiting-confirm'
    m.awaitingSubmissionId = sub.id
    DB['matches'][matchId] = m
    return sub

@app.post('/matches/{matchId}/confirm', response_model=Match)
def confirm_score(matchId: str, body: Dict):
    if matchId not in DB['matches']:
        raise HTTPException(404, 'Match not found')
    m: Match = DB['matches'][matchId]
    if m.status != 'awaiting-confirm' or not m.awaitingSubmissionId:
        raise HTTPException(400, 'No pending submission')
    subId = body.get('submissionId')
    if subId != m.awaitingSubmissionId:
        raise HTTPException(400, 'Submission mismatch')
    sub: Submission = DB['submissions'][subId]
    m.scores = sub.scores
    totalA = sum(s.a for s in m.scores)
    totalB = sum(s.b for s in m.scores)
    m.winner = m.teamA if totalA > totalB else m.teamB
    m.status = 'final'
    m.awaitingSubmissionId = None
    DB['matches'][matchId] = m
    DB['submissions'][subId].state = 'opponent-confirmed'
    return m

@app.get('/divisions/{divId}/standings')
def standings(divId: str):
    table = compute_standings(divId)
    def team_label(t: Team):
        if t.playerB:
            a = DB['users'][t.playerA]; b = DB['users'][t.playerB]
            return f"{a.firstName} {a.lastName} / {b.firstName} {b.lastName}"
        else:
            a = DB['users'][t.playerA]
            return f"{a.firstName} {a.lastName}"
    display = []
    for teamId, row in table.items():
        t = DB['teams'][teamId]
        display.append({'teamId': teamId, 'team': team_label(t), **row})
    display.sort(key=lambda r: (-r['W'], -r['PD'], -r['PF']))
    return {'rows': display}
