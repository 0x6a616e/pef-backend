{
  description = "A Nix-flake-based Python development environment";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";

  outputs = { self, nixpkgs }:
    let
      supportedSystems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      forEachSupportedSystem = f: nixpkgs.lib.genAttrs supportedSystems (system: f {
        pkgs = import nixpkgs { inherit system; };
      });
    in
    {
      devShells = forEachSupportedSystem ({ pkgs }: {
        default = pkgs.mkShell {
          LD_LIBRARY_PATH = "${pkgs.stdenv.cc.cc.lib}/lib";
          venvDir = ".venv";
          packages = with pkgs; [ python313 ] ++
            (with pkgs.python313Packages; [
              pip
              venvShellHook
            ]);
        };
      });
      packages = builtins.mapAttrs (system: pkgs: rec {
        default = pkgs.dockerTools.streamLayeredImage {
          name = "teh-awesome-container";
          tag = "v1";

          contents = pkgs.buildEnv {
            name = "env1";
            paths = [
              pkgs.hello
              pkgs.perl
              pkgs.python3
              ./.
            ];
          };

          config = {
            Cmd = ["hello"];
          };
        };
      }) nixpkgs.legacyPackages;
    };
}
