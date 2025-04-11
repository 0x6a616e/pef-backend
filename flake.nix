{
  description = "A Nix-flake-based Python development environment";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/release-24.11";

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
          packages = with pkgs; [ python313 nodejs_23 ] ++
            (with pkgs.python313Packages; [
              pip
              venvShellHook
            ]);
        };
      });
    };
}
