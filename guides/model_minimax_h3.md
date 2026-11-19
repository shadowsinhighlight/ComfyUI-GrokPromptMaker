TARGET MODEL: MiniMax H3 (Hailuo 3). H3 generates video and stereo audio together and is trained on a fixed prompt format. Follow it exactly.

OUTPUT FORMAT, three fields in this order, each label on its own line followed by its text:

integrated_multimodal_description:
<the whole audiovisual timeline>

overall_soundscape:
<one paragraph, 1 to 4 sentences, or N/A>

non_diegetic_music:
<1 to 3 sentences, or N/A>

For image to video, put this alignment line first, then a blank line, then the three fields:
For the target video, at 0.00 seconds into the target video, the reference picture is fully referenced as the first frame.

integrated_multimodal_description rules:
- Open with a style term (for example "Live-action, cinematic", "3D CG", "claymation", "2D anime"), then the look: palette, light, lens, grain. For image to video, take the style from the start image.
- Write shots as [Shot 1], [Shot 2] ... [Shot 1] has NO timestamp. Every later shot starts with its cut time: "[Shot 2] At 00:04.000, the camera cuts to ...". Cut times strictly increase and the shots together fill the clip length.
- Shot count: one shot for 5 to 6 seconds, two for about 8 seconds, three or four for 10 to 15 seconds. Below about 2.5 seconds a shot, geography stops holding.
- Cut only to show new information (subject, space, state, viewpoint, time). Otherwise move the camera. H3 cuts by default, so for one continuous take say "one continuous take, no cuts".
- Each shot: shot size in plain words first (extreme wide / wide / medium / close-up / extreme close-up), then where the camera is, then who is where, then what they do.
- Camera motion vocabulary: Static Shot, Push In, Pull Out, Zoom, Pan, Tilt, Truck, Pedestal, Arc Shot, Tracking Shot, Shake, POV, Roll. Add "small"/"large" and "slow"/"fast" only when not medium. One move per shot.
- Dialogue: a speaking character gets a speaker ID in order of first vocalisation: (S1), (S2). Describe the voice once, at first use. The spoken line goes in <d> with a language tag: <d>[English] Exact words here.</d> Never translate or alter the words. Silent characters get no ID.
- Voiceover: write "says in an off-screen voiceover" and state that the on-screen character's lips stay closed.
- Text that must be legible on screen goes in English double quotes.
- Any sound tied to a specific moment (a door slam, a line of dialogue, a radio playing in the room) is written here, in the shot where it happens.

overall_soundscape rules: ambience and physical sound across the whole clip: room tone, two or three ambient sounds, one or two action sounds. No dialogue and no music.

non_diegetic_music rules: only score the audience hears and the characters do not. Describe instruments, tempo, rhythm and dynamics, not mood words. Use N/A unless the user wants music. Music a character could hear belongs in the description instead.

Craft rules that matter for H3:
- Describe positions, not movements to them. Say where the camera IS ("the camera stands three paces in front of her at chest height, facing her"). If it must move, name the state it ends in ("it keeps drawing back until all four are in frame"), not an amount such as "rotates 180 degrees".
- Lock a static camera explicitly and more than once: "locked off, does not push in, does not pull back, does not zoom, does not pan or tilt". H3 adds a slow push-in otherwise.
- Sequence actions with visible completion states, not "then"/"while"/"as". Two actions in one sentence read as simultaneous. Example: "she says goodbye with the phone still at her ear, and her mouth closes and comes to rest. Only after her lips are closed and still does she lower the phone."
- Anchor blocking to two fixed landmarks ("seated on the far side of the table, window over her left shoulder") and restate it in every shot: blocking resets at cuts. Say which side of a barrier people are on.
- One clear action per shot. About three moving subjects is the safe limit; extras must stay static.
- Never negate an object ("no sunglasses" puts sunglasses in). Describe the space full of what is really there. Negatives are fine for camera behaviour and composition only.
- Freezes and held poses render well; continuous spins smear. Name real moves, and name the transition between standing and floor.
- Crowds: describe loosely as a shape (coats, raised arms), no individual faces. Faces only in close-ups.
- Sound follows the action verbs: H3 makes foley from what you describe, so choose verbs for the sound you want.
- H3 takes contrast words literally. Avoid: crushed blacks, high contrast, punchy, vibrant, saturated, crisp, sharp, HDR. Prefer: lifted blacks, shadow detail, highlights rolling off softly, low contrast, flat film grade, muted colour, soft halation, fine film grain.
- Avoid vague mood words ("emotional", "cinematic feel"): the model cannot act on them.

Length: 120 to 250 words of description for a single shot, up to about 450 for a multi-shot clip.
