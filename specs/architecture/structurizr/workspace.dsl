workspace "CHANGE_ME Platform" "C4 model derived from specs/architecture and CAP requirements." {

  model {
    user = person "User" "End user of the product." {
      tags "Person"
    }

    platform = softwareSystem "CHANGE_ME Platform" "Distributed domain services with a Shell-composed UI." {
      tags "SoftwareSystem"

      shell = container "Shell Application" "Owns global navigation, authentication integration, theming, and composes domain UI modules." "Web/Mobile App" {
        tags "Container,Shell"
      }

      domainUIs = container "Domain UI Modules" "Independently delivered UI modules integrated only via the Shell entrypoint contract (e.g., mount(context))." "Federated UI Modules" {
        tags "Container,DomainUI"
      }

      gateway = container "API Gateway / BFF (optional)" "Edge/API aggregation layer. Does not replace domain-level authorization." "HTTP API" {
        tags "Container,Gateway"
      }

      auth = container "Auth Domain" "Sole issuer of access tokens (JWT) and refresh tokens. Publishes JWKS and rotates keys." "Service" {
        tags "Container,Auth"
      }

      exampleDomain = container "Example Domain Service (DOM-0002)" "Placeholder domain service. Validates JWT locally using cached JWKS. Replace with a real business domain." "Service" {
        tags "Container,DomainService"
      }
    }

    user -> shell "Uses" "HTTPS"

    shell -> domainUIs "Loads & mounts" "Entrypoint contract"

    shell -> auth "Authenticates / refreshes" "OIDC/OAuth2"

    domainUIs -> gateway "Calls APIs with access token" "HTTPS + JWT (access)"

    gateway -> auth "Routes auth requests" "HTTPS + JWT (access)"

    domainUIs -> exampleDomain "(Optional) calls domain API directly" "HTTPS + JWT (access)"
    gateway -> exampleDomain "Routes requests" "HTTPS + JWT (access)"
    exampleDomain -> auth "Periodically fetches JWKS" "HTTPS"
  }

  views {
    systemContext platform "SystemContext" "System context (C4)" {
      include user
      include platform
      autolayout lr
    }

    container platform "Containers" "Container diagram (C4)" {
      include user
      include *
      autolayout lr
    }

    styles {
      element "Person" {
        shape person
        background "#08427b"
        color "#ffffff"
      }

      element "SoftwareSystem" {
        background "#1168bd"
        color "#ffffff"
      }

      element "Container" {
        background "#438dd5"
        color "#ffffff"
      }

      element "Shell" {
        background "#2d936c"
        color "#ffffff"
      }

      element "DomainUI" {
        background "#3a7ca5"
        color "#ffffff"
      }

      element "Auth" {
        background "#7b2cbf"
        color "#ffffff"
      }

      element "DomainService" {
        background "#1f7a8c"
        color "#ffffff"
      }

      element "Gateway" {
        background "#ff7f11"
        color "#111111"
      }
    }
  }
}
