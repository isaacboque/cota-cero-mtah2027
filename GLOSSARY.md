# Glossary

**Control**: a player having the ball at an instant. An event, not a state. _Avoid_: possession (for the instant).

**Possession**: a spell of time in which one team has the ball while it is alive. The unit spellF1 scores. _Avoid_: control (for the spell).

**Possession change**: the end of one team's possession followed by the other team's. In IDSSE reference labels it only counts if the new owner keeps the ball ≥ 1 s with the ball alive and the change is not within 1 s of a dead-ball spell. _Avoid_: turnover (not every change is a turnover in the football sense).

**Unknown owner**: an alive frame whose source gives no owning team. Not scored. _Avoid_: away (kloppy's default for it).
