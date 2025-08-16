graph [
  directed 1

  // Node untuk kelas User
  node [
    id 1
    label "User"
    comment "Represents a user in a microblogging platform (e.g., Twitter, Tumblr)."
  ]

  // Node untuk kelas ProfileSettings
  node [
    id 2
    label "ProfileSettings"
    comment "Represents profile customization settings for the user."
  ]

  // Edge untuk disjoint relation
  edge [
    source 1
    target 2
    label "disjointWith"
  ]

  // Data property nodes dengan kelas User sebagai domain
  node [
    id 3
    label "hasEmail"
    domain "User"
    range "xsd:string"
    comment "Stores the email address associated with the user's account."
  ]
  node [
    id 4
    label "hasPassword"
    domain "User"
    range "xsd:string"
    comment "Stores the password for the user's account."
  ]
  node [
    id 5
    label "hasBirthday"
    domain "User"
    range "xsd:date"
    comment "Stores the user's birth date."
  ]
  node [
    id 6
    label "hasSecuritySettings"
    domain "User"
    range "xsd:string"
    comment "Contains the user's security settings (e.g., two-factor authentication status)."
  ]
  node [
    id 7
    label "hasSubscriptionStatus"
    domain "User"
    range "xsd:string"
    comment "Indicates the user's subscription status (e.g., premium, free)."
  ]
  node [
    id 8
    label "hasNotificationsSetting"
    domain "User"
    range "xsd:string"
    comment "Specifies the user's notifications settings (e.g., email notifications enabled)."
  ]
  node [
    id 9
    label "hasPrivacySetting"
    domain "User"
    range "xsd:string"
    comment "Specifies the user's privacy settings (e.g., public profile, private account)."
  ]
  node [
    id 10
    label "hasLogoutStatus"
    domain "User"
    range "xsd:boolean"
    comment "Indicates if the user is currently logged out of the platform."
  ]

  // Object property nodes antara User dan ProfileSettings
  edge [
    source 2
    target 1
    label "canEditProfile"
    comment "Indicates permission to edit profile information."
  ]
  edge [
    source 2
    target 1
    label "canEditAvatar"
    comment "Indicates permission to edit profile avatar."
  ]
  edge [
    source 2
    target 1
    label "canEditHeader"
    comment "Indicates permission to edit profile header."
  ]

  // Node untuk kelas ContentCreation
  node [
    id 11
    label "ContentCreation"
    comment "Represents actions related to creating and managing content on a microblogging platform."
  ]

  // Object properties dengan ContentCreation sebagai domain
  edge [
    source 11
    target 1
    label "makePost"
    comment "Indicates the action of creating a new post by the user."
  ]
  edge [
    source 11
    target 1
    label "addToQueue"
    comment "Allows a user to add a post to a queue for later publication."
  ]
  edge [
    source 11
    target 1
    label "schedulePost"
    comment "Schedules a post to be published at a specified time."
  ]
  edge [
    source 11
    target 1
    label "saveAsDraft"
    comment "Saves a post as a draft for future editing or posting."
  ]
  edge [
    source 11
    target 1
    label "postAsPrivate"
    comment "Posts content with a private visibility setting."
  ]
  edge [
    source 11
    target 1
    label "addContentLabel"
    comment "Adds a label or tag to the content for categorization or filtering."
  ]
  edge [
    source 11
    target 1
    label "controlReblogRetweet"
    comment "Enables or disables the option for other users to reblog or retweet the content."
  ]
  edge [
    source 11
    target 1
    label "postMedia"
    comment "Posts media content such as images, videos, or GIFs."
  ]
  edge [
    source 11
    target 1
    label "postLink"
    comment "Posts a link within the content."
  ]

  // Data properties dengan kelas ProfileSettings sebagai domain
  node [
    id 12
    label "hasBio"
    domain "ProfileSettings"
    range "xsd:string"
    comment "Stores the bio or description on the user's profile."
  ]
  node [
    id 13
    label "hasLocation"
    domain "ProfileSettings"
    range "xsd:string"
    comment "Indicates the user's location as shown on their profile."
  ]
  node [
    id 14
    label "hasWebsite"
    domain "ProfileSettings"
    range "xsd:string"
    comment "Contains the website link provided by the user in their profile."
  ]
  node [
    id 15
    label "hasBirthDate"
    domain "ProfileSettings"
    range "xsd:date"
    comment "Records the user's birth date displayed on their profile."
  ]
  node [
    id 16
    label "hasTips"
    domain "ProfileSettings"
    range "xsd:string"
    comment "Stores any tips or notable quotes the user chooses to display on their profile."
  ]
]
