# Mr & Miss Fresh 2026 voting portal

Static Firebase-backed voting portal for Freshers Night on December 4, 2026. Voters do not create accounts. They select a nominee, transfer money at **₦100 per vote**, and submit payment details. A Firebase-authenticated admin reviews pending submissions. Only approved submissions increment nominee votes, using `amount / 100`.

## Netlify deployment

1. Connect this repository to Netlify.
2. Netlify will use `netlify.toml`: build command `npm run build`, publish directory `.`.
3. Keep `firebase-config.js` configured for the Firebase project used by the event.
4. Deploy `firestore.rules` through Firebase CLI or the Firebase console.
5. Enable Firebase Authentication > Email/Password and create the admin user.
6. In Firestore, create `admins/{ADMIN_UID}` with any fields. The document ID must exactly match the Firebase Auth UID.

## Firestore setup

Create `settings/event` with `status: "active"` and `categories: ["MR FRESH 2026", "MISS FRESH 2026"]`. Create nominee documents in `nominees` with `name`, `category`, `votes: 0`, and optionally `image`. The admin dashboard can be extended to import the official nominee ZIP once it is supplied.

The payment account is centralized in `js/app.js`: **Miebai Joy Oyindobra · 6527209550 · Moniepoint MFB**.

## Data model

- `nominees/{id}`: public nominee records and approved `votes` total.
- `paymentSubmissions/{id}`: pending/approved/rejected payment claims, voter contact details, amount, and calculated `voteUnits`.
- `admins/{uid}`: allow-list for Firebase-authenticated admins.
- `settings/event`: event status and categories.

## Admin login

Use Firebase Authentication with Email/Password. Create an admin user with the email `admin@freshersnight2026.com` and a strong password you choose, then create `admins/{USER_UID}` in Firestore. The password is intentionally not stored in this repository.

The uploaded photo manifest is in `data/official-nominees.json`. All photos are intentionally in one combined `MR & MISS FRESH 2026` pool so voters can identify the nominees from the photos without forced gender labels.
