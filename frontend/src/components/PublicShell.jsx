const logo = `${import.meta.env.BASE_URL}sda-logos.png`

function Clock() {
  return (
    <svg width="26" height="26" viewBox="0 0 46 46" aria-hidden="true">
      <circle cx="23" cy="23" r="19" fill="none" stroke="#F2B230" strokeWidth="3.5" />
      <path d="M23 11V23L31 28" fill="none" stroke="#F2B230" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

/** Blue page with the church header, used by the registration and thank-you pages. */
export default function PublicShell({ hero = true, children }) {
  return (
    <div className="pub">
      <main className="pub-inner">
        <img className="pub-logos" src={logo} alt="Seventh-day Adventist Church logos" width="250" height="84" />
        <div className="church">
          <b>Seventh-day Adventist Church</b>
          <span>Mount Kenya University</span>
        </div>

        {hero && (
          <>
            <p className="invites">INVITES EVERYONE TO</p>
            <h1 className="hero-title">
              <span className="script">Gongoni</span>
              <span className="mission">
                mission <span className="badge27">27</span>
              </span>
            </h1>
            <p className="dates">
              <Clock />
              <span>25 April – 9 May 2027 · Kilifi County</span>
            </p>
          </>
        )}

        {children}

        <footer className="pub-foot">
          <b>Kambire Dhunia · Go tell the world</b>
          <span>@MKUSDA church · Mkusdachurch.org</span>
        </footer>
      </main>
    </div>
  )
}
