(add-to-load-path "vendor/guix-systole/systole")

(use-modules (guix build-system trivial)
             (gnu packages bash)
             (gnu packages base)
             (guix gexp)
             (guix packages)
             (guix profiles)
             ((guix licenses) #:prefix license:)
             (ice-9 match)
             (srfi srfi-1)
             (systole packages ros2 jazzy))

;; A manifest containing turtlesim and ros2run directly makes Guix's profile
;; hooks repeatedly traverse ROS's dense propagated-input graph and can exhaust
;; memory.  Build one symlink union instead: the manifest then has one entry,
;; while the union contains only these tools and their runtime dependencies.
(define turtlesim-jazzy-environment
  (package
    (name "ros-turtlesim-jazzy-environment")
    (version "1.8.3")
    (source #f)
    (build-system trivial-build-system)
    (arguments
     (list #:modules '((guix build union))
           #:builder
           (with-imported-modules '((guix build union))
             #~(begin
                 (use-modules (guix build union))
                 (union-build #$output
                              (map cdr %build-inputs)
                              #:create-all-directories? #t)))))
    (inputs
     (let ((direct (list ros-turtlesim-jazzy ros-ros2run-jazzy)))
       (delete-duplicates
        (append direct
                (append-map
                 (lambda (package)
                   (map (match-lambda ((_ input . _) input))
                        (package-transitive-propagated-inputs package)))
                 direct))
        eq?)))
    (native-search-paths (package-native-search-paths ros-jazzy))
    (home-page "https://docs.ros.org/en/jazzy/Tutorials/Beginner-CLI-Tools/Introducing-Turtlesim/Introducing-Turtlesim.html")
    (synopsis "ROS 2 Jazzy turtlesim environment")
    (description
     "Small union environment containing ROS 2 Jazzy turtlesim, ros2run, and
their complete runtime dependency closure.")
    (license license:asl2.0)))

(packages->manifest (list turtlesim-jazzy-environment bash-minimal coreutils))
