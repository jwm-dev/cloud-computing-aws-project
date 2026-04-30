# cloud-computing-aws-project
Repository for the OUPI SDI-3213 AWS semester project.

- [ ] Backend: Python FastAPI server with Hidden Agenda environment simulation
  - [ ] `backend/main.py` - FastAPI app entry point
  - [ ] `backend/environment/hidden_agenda.py` - Hidden Agenda gym environment
  - [ ] `backend/api/experiments.py` - Experiment dispatch/status endpoints
  - [ ] `backend/api/analytics.py` - Analytics/metrics endpoints
  - [ ] `backend/api/replays.py` - Replay storage/retrieval endpoints
  - [ ] `backend/storage/s3_client.py` - S3 integration
  - [ ] `backend/requirements.txt`
  - [ ] `backend/Dockerfile`
- [ ] Frontend: React dashboard
  - [ ] `frontend/src/App.jsx` - Root component with routing
  - [ ] `frontend/src/components/Dashboard.jsx` - Overview dashboard
  - [ ] `frontend/src/components/ExperimentDispatch.jsx` - Launch experiments
  - [ ] `frontend/src/components/Analytics.jsx` - Metrics & charts
  - [ ] `frontend/src/components/ReplayViewer.jsx` - Game replay viewer
  - [ ] `frontend/package.json`
  - [ ] `frontend/Dockerfile`
- [ ] Infrastructure
  - [ ] `infrastructure/terraform/main.tf` - EC2 + S3 resources
  - [ ] `infrastructure/terraform/variables.tf`
  - [ ] `infrastructure/terraform/outputs.tf`
  - [ ] `infrastructure/terraform/user_data.sh` - EC2 startup script
- [ ] Root: `docker-compose.yml`, updated `README.md`, `.gitignore`

# Outline

An RL-agent gym deployed from a portable docker container, on AWS with an EC2 instance and an S3 backend available on a public, free Cloudflare URL that implements the game "Hidden Agenda":

```
Hidden Agenda Environment
Hidden Agenda is an n-player environment, where nc players are Crewmates (the team with numerical
advantage), ni are Impostors (the team with information advantage), and nc > ni, nc + ni = n
(Figure 1). The Crewmates are unaware of the roles of the other players, while the Impostor knows
the roles of all players. For all the experiments presented here, we used five players: ni = 1 Impostor
and nc = 4 Crewmates. The Crewmates’ goal is to refuel their ship by collecting energy fuel cells
that are scattered around the ship, and depositing them in a central location. The Impostor’s aim is to
prevent the Crewmates from achieving their goal by freezing them with a short-range freezing beam.
The environment was implemented in Lab2D [4] using the component system described in Melting
Pot [20].
At the beginning of an episode, each player is randomly assigned a role and color for their avatar
in the environment and initialized to a location near the center of the game map. Note, there is no
correlation between color and role.
2.1 Overview of Gameplay
Like other social deduction games, Hidden Agenda has two alternating phases: a situation phase and
a voting phase (Figure 2).
Situation Phase. During the situation phase, players can move around, pick up the green fuel cells
found in the rooms at the corners of the map, and add it to their inventory. The inventory can hold
up to 2 fuel cells at any given time. Players can deposit the fuel down the grate in the center of the
2Videos of trained reinforcement learning agents exhibiting the aforementioned behaviors are available here:
https://youtu.be/k2POZTLONvk
2
Figure 1: The Hidden Agenda environment, illustrating key game dynamics including tasks, freezing,
and voting. The environment is a 2D world consisting of a grid of 40 × 31 sprites. The environment
is roughly organised in rooms, with rooms near the four corners of the grid containing fuel cells that
can be picked up and a central room where the fuel cells can be deposited. The central-upper room
is where deliberation happens. This deliberation room is only accessible during voting phases and
includes a jail where voted out agents remain for the rest of the episode.
Figure 2: The anatomy of an episode: Hidden Agenda is split between the situation and voting phases.
During the situation phase, all players can move around the environment collecting or depositing fuel
cells and the impostors can fire a freezing beam. During the voting phase, players can cast public
votes and observe the votes of everyone in the previous time step.
map, clearing their inventory of fuel and increasing a global progress bar counting the amount of fuel
deposited against a goal necessary for the Crewmates to win.
The Impostor have access to a special action that fires a freezing beam. If the beam hits a Crewmate,
it freezes them in place for the remainder of the game. Frozen players are thus inactivated and cannot
take any further actions. This is the main mechanism by which the Impostor prevents Crewmates
from winning the game.
Voting Phase. The voting phase is initiated whenever the Impostor’s freeze action is witnessed
by an active Crewmate who was not within the freeze radius, or when 200 timesteps have elapsed
since the end of the last voting phase or the beginning of the episode. At the start of the voting phase,
players are teleported to a voting room where their only available actions are to vote for a player
or abstain from voting. The voting phase lasts 25 timesteps and players can see the votes of all the
players from the previous voting timestep. In the first voting timestep of the phase, all active players
are considered to have abstained. At the last step of the voting phase, the final votes are tallied. If a
player receives at least half of the final votes from active players (where active players are defined as
all players who have not been previously inactivated), they are teleported to jail, where they cannot
take any further actions and are inactivated for the rest of the game.
Win Conditions. The game ends when one of the following conditions is reached:
• Crewmates collect and deposit enough fuel cells to power their ship (Crewmates win).
• The Impostor is voted out during a voting round (Crewmates win).
3
• All Crewmates but one are either frozen or voted out (Impostor wins). This win condition is
split into two scenarios: one where the last Crewmate to be inactivated is frozen and one
where the last Crewmate to be inactivated was voted out during a voting round.
• 3000 timesteps have elapsed (a draw).
2.2 Environment Details
Observations. At every timestep, players receive as observations:
• an RGB image of their local view of the game map (with shape (88, 88, 3)),
• the percent of their personal inventory occupied with fuel cells...
```

