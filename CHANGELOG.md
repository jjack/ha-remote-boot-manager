# Changelog

## [0.5.3](https://github.com/jjack/ha-grubstation/compare/v0.5.2...v0.5.3) (2026-05-18)


### Features

* adding unregister_host webhook to make uninstalling easier ([7171aec](https://github.com/jjack/ha-grubstation/commit/7171aec68a1d0e91a1b8ba1321c64ba8f172befb))


### Bug Fixes

* adding 'Agent Status' sensor when the agent checks in, even if there aren't any boot options pushed yet ([93463ef](https://github.com/jjack/ha-grubstation/commit/93463eff4b0684e360abe3ecd06c5ec6105e4fe5))
* formatting files ([836ae5f](https://github.com/jjack/ha-grubstation/commit/836ae5f7c07fa7337f3f46373faae123957506f0))
* removing silly custom history because HA has it built in. how novel. ([828527d](https://github.com/jjack/ha-grubstation/commit/828527d1333c82b9a10284cc930e35fe786761e8))
* running ruff ([e4cf18e](https://github.com/jjack/ha-grubstation/commit/e4cf18ef2cbaab5c9576f8623790cbc03168ad7c))
* using host entity object instead of raw strings for the turn_off service to make it easier to work with ([84d115a](https://github.com/jjack/ha-grubstation/commit/84d115a4089d245c1c669284c339ec19318bb13d))

## [0.5.2](https://github.com/jjack/ha-grubstation/compare/v0.5.1...v0.5.2) (2026-05-15)


### Features

* adding entity name to list of hosts to make it easier to figure out what's what ([11f7d22](https://github.com/jjack/ha-grubstation/commit/11f7d22e38a8ca1ecee780868bb226c8edd1f452))
* adding error handling for daemon /shutdown ([0ce27f9](https://github.com/jjack/ha-grubstation/commit/0ce27f9b901c1bc04e0f5ae75c9f2914a53b2f6a))
* adding host os and version to sensors ([c5e366a](https://github.com/jjack/ha-grubstation/commit/c5e366a777263ee1b612d3382b7818709f6f2fa0))


### Bug Fixes

* adding error checking for turn off command ([97fd775](https://github.com/jjack/ha-grubstation/commit/97fd7756716bd255035e07faeb18767a114e673a))
* correct use of ATTR vs CONST ([735bde0](https://github.com/jjack/ha-grubstation/commit/735bde02648d603d52c97df078640729f487f7f6))
* removing useless context ([882a99f](https://github.com/jjack/ha-grubstation/commit/882a99fe31aca4b1ac990232ebfacedbf56226dd))

## [0.5.1](https://github.com/jjack/ha-grubstation/compare/v0.5.0...v0.5.1) (2026-05-13)


### Features

* adding extra entity logging ([30e568e](https://github.com/jjack/ha-grubstation/commit/30e568edc9b1dd2d0c88272d27fee2c7c643a746))


### Bug Fixes

* adding default turn_off action to prevent errors in the options flow ([73724c3](https://github.com/jjack/ha-grubstation/commit/73724c38af2ea4c94c4b5206107196b5657bf351))
* adding turn off action to ui ([02a15a4](https://github.com/jjack/ha-grubstation/commit/02a15a40e02f6269d450f7a0a54fc4a6ebe2cb82))
* ensuring that the healthcheck sensors get the same DeviceInfo as everything else ([05dbfa5](https://github.com/jjack/ha-grubstation/commit/05dbfa55cf2d0bbbeed9896bc9db680895918d99))
* fixing issue where boot option gets consumed without the token ([5a86894](https://github.com/jjack/ha-grubstation/commit/5a86894d0604cde8476fa5d62208a75e4412bec5))

## [0.5.0](https://github.com/jjack/ha-grubstation/compare/v0.4.4...v0.5.0) (2026-05-11)


### Features

* adding support for remote agent agent ([6f6762b](https://github.com/jjack/ha-grubstation/commit/6f6762bda0e0d1c292beec168b36ea9f6e618042))


### Bug Fixes

* correcting import name ([e9c8e8a](https://github.com/jjack/ha-grubstation/commit/e9c8e8a487396a7f05b9aa968ed58caf54d483d1))
* lowercasing the domain name in manifest.json, too ([a712a95](https://github.com/jjack/ha-grubstation/commit/a712a95fcc2593f022d9cd43b92a5b4141592e6e))
* lowercasing the domain name, it got caught up in search and replace ([8045b79](https://github.com/jjack/ha-grubstation/commit/8045b79daba07c081d124dd00d264c85dd882806))

## [0.4.4](https://github.com/jjack/ha-grub-os-selector/compare/v0.4.3...v0.4.4) (2026-05-07)


### Bug Fixes

* paranoid check you're not supposed to direct string compare tokens ([b8c3c64](https://github.com/jjack/ha-grub-os-selector/commit/b8c3c64f8f0c16ed0f7ff28baa9b060ef5bcbe27))
* preventing possible executor exhaustion with spammy failed bootloaders ([9304f65](https://github.com/jjack/ha-grub-os-selector/commit/9304f65c63083a13b7397216bebfbb5115d2e73a))
* preventing possible injection attacks with grub bootloader ([4653111](https://github.com/jjack/ha-grub-os-selector/commit/46531119a258b010f996a80a81325eea2c453668))
* removing unnecessary temporary variable ([153dbd6](https://github.com/jjack/ha-grub-os-selector/commit/153dbd624bec421d80899e848fdde0a37f5f2c41))
* using json.loads to be less strict in case someone forgets a "Content-Type: application/json" ([bc2b714](https://github.com/jjack/ha-grub-os-selector/commit/bc2b71491c7133d3c9956019dbfad1105ebb3c83))

## [0.4.3](https://github.com/jjack/ha-remote-boot-manager/compare/v0.4.1...v0.4.3) (2026-05-06)


### Miscellaneous Chores

* force release ([b0c4f5b](https://github.com/jjack/ha-remote-boot-manager/commit/b0c4f5b630e633b2276cf04955cee37cc69451f4))

## [0.4.1](https://github.com/jjack/hass-remote-boot-manager/compare/v0.4.0...v0.4.1) (2026-05-06)


### Bug Fixes

* adding  _attr_name back ([31db373](https://github.com/jjack/hass-remote-boot-manager/commit/31db3736636123d54da500594181f999a1fe826f))
* adding symlinks to dark icons ([4b1ac33](https://github.com/jjack/hass-remote-boot-manager/commit/4b1ac33a00a8143046b352d58553d6b0647f2a12))
* correcting potential memory leak during task cancellation ([c3c1148](https://github.com/jjack/hass-remote-boot-manager/commit/c3c1148a1a13d4cf0b1a3aa87bfb6257ab66cb08))
* ensuring webhooks have a mac address in the payload ([09a0625](https://github.com/jjack/hass-remote-boot-manager/commit/09a06251bef93bbb19e51a058d4d85c63d2617dc))
* letting users actually add turn_off scripts. and now they can edit (temporarily) broadcast stuff for testing. ([08b596c](https://github.com/jjack/hass-remote-boot-manager/commit/08b596c06927cabc700449cd0dea18d0ed2bdc86))
* making sure that the bootloader view is registered only once ([642d1b8](https://github.com/jjack/hass-remote-boot-manager/commit/642d1b8b4f55b37846e961a860d833ce475e3dde))
* updating tests to no longer use the global manager ([7ebc599](https://github.com/jjack/hass-remote-boot-manager/commit/7ebc5998d25a4a5cd4ec06e1f5303540848c29de))

## [0.4.0](https://github.com/jjack/hass-remote-boot-manager/compare/v0.3.1...v0.4.0) (2026-05-04)


### Features

* adding backwards compatability to the switch ([febab72](https://github.com/jjack/hass-remote-boot-manager/commit/febab725e84fa71de6e1e14ad3a181798c886cd6))
* adding backwards compatability to the switch ([0bfbab5](https://github.com/jjack/hass-remote-boot-manager/commit/0bfbab5b5a3b12d5e424c577a15ae9444539c2e3))
* letting people use buttons or switches, depending on their need and preferences ([ac4152c](https://github.com/jjack/hass-remote-boot-manager/commit/ac4152c71a68d9ecfbc0939675d4a384c5e7fc7b))
* reading configuration.yaml entries to support wake_on_lan migration ([eae0704](https://github.com/jjack/hass-remote-boot-manager/commit/eae070499bed5d9b8b46da51094ad0991f397e73))
* replicating turn_off functionality ([93c2b22](https://github.com/jjack/hass-remote-boot-manager/commit/93c2b22c225b75ffecec731611652060f51f0774))
* requiring a token (the webhook id) to actually consume the next boot option so that you can test things ([4c94143](https://github.com/jjack/hass-remote-boot-manager/commit/4c9414335c53795a45273a150515aa7db9ec6311))


### Bug Fixes

* adding missing services.yaml to repo ([730bf4a](https://github.com/jjack/hass-remote-boot-manager/commit/730bf4aa1835cf7bd498e7d30975608de4226610))
* better handling of switch polling.. ([ce3bf4b](https://github.com/jjack/hass-remote-boot-manager/commit/ce3bf4bb3a251da0443658be596fb83e5d8cfbec))
* no longer immediately toggling switches off ([d1e3118](https://github.com/jjack/hass-remote-boot-manager/commit/d1e3118005cd08e528a7667ae3957177bc09790d))
* no longer using the global manager ([01863c3](https://github.com/jjack/hass-remote-boot-manager/commit/01863c358e9782a2608ed7e20276563d9da07de6))
* removing direct yaml config setup. that was not at all what I was trying to do ([a989cb5](https://github.com/jjack/hass-remote-boot-manager/commit/a989cb564dfc9d9cd4d70e073ea79ca7aa9bd380))
* removing RestoreEntity and using Store for everything ([1212ecd](https://github.com/jjack/hass-remote-boot-manager/commit/1212ecd934773e5fd9680afe6a4b502680d3219b))

## [0.4.0-beta.0](https://github.com/jjack/hass-remote-boot-manager/compare/v0.3.1-beta.0...v0.4.0-beta.0) (2026-04-29)


### Features

* added initial button and select entities ([dccbd02](https://github.com/jjack/hass-remote-boot-manager/commit/dccbd02b706d262c22280103b98c3741a260a74e))
* adding broadcast address and port ([54e1695](https://github.com/jjack/hass-remote-boot-manager/commit/54e16951145b96fcfe9718fa233eda235e145898))
* adding device info to integration page ([ea15a05](https://github.com/jjack/hass-remote-boot-manager/commit/ea15a0585cdd88fa55c38b5a7a80dfe327f6f568))
* adding logos and icons ([d2e9548](https://github.com/jjack/hass-remote-boot-manager/commit/d2e954829f2048db824e1722f02843621ea51d8f))
* adding release please for release versioning ([b509f8a](https://github.com/jjack/hass-remote-boot-manager/commit/b509f8ace50acec9be792220bf24ad3ffc8f8636))
* adding unauthenticated view for bootloader configs ([d7cfde0](https://github.com/jjack/hass-remote-boot-manager/commit/d7cfde0f20ab7f7b023d70bb14a03c0877031071))
* allowing a custom webhook id ([20e2319](https://github.com/jjack/hass-remote-boot-manager/commit/20e2319bff2a8dfe56471e352479dd1abf5724db))
* always generating the webhook id for security ([ff1ab2d](https://github.com/jjack/hass-remote-boot-manager/commit/ff1ab2d2209c4f9694a98f013141ad18d2db332f))
* can now auto-generate webhook_ids for security ([f8d94e3](https://github.com/jjack/hass-remote-boot-manager/commit/f8d94e36565dc95508262327519b058bf3148285))
* can now select an OS ([0e8ac2f](https://github.com/jjack/hass-remote-boot-manager/commit/0e8ac2f7ad7dc072ff80be8263864b711a1d9579))
* can regenerate the webhook id ([421820a](https://github.com/jjack/hass-remote-boot-manager/commit/421820abb57eee7388345acad3481c1b12ef819e))
* can remove servers from the ui ([571c815](https://github.com/jjack/hass-remote-boot-manager/commit/571c8158456a7dfdb87888a8b99cccee776b5ad7))
* home assistant now starts and lets me almost add the integration ([478848e](https://github.com/jjack/hass-remote-boot-manager/commit/478848efedd8ef9ad5b2f53e918cee25f88d91cc))
* now automatically deleting entries when the integration is removed ([b53f508](https://github.com/jjack/hass-remote-boot-manager/commit/b53f5080d5c0735bcb84cdd99e91c620c9c3eb3e))
* registering first webhook for data ingestion ([27e77b8](https://github.com/jjack/hass-remote-boot-manager/commit/27e77b8c36e1815d125d648a105ef6d7ded4f8f7))
* the button now buttons ([6366323](https://github.com/jjack/hass-remote-boot-manager/commit/63663238bfab37c59c4ea41d2c67976ec16ff8c5))
* using RestoreEntity to maintain state across reboots ([b1eee5a](https://github.com/jjack/hass-remote-boot-manager/commit/b1eee5ac8e803475a9bc2f4a51c5372654d6f81b))
* validating payload for security and consistency ([0a16319](https://github.com/jjack/hass-remote-boot-manager/commit/0a1631975821bd5e90664947ff3c81cb9eb02231))


### Bug Fixes

* adding missing wakeonlan dependency ([23f5114](https://github.com/jjack/hass-remote-boot-manager/commit/23f51140726e3b7311e74b90ff694fbd7ca6e022))
* adding new platforms and removing dead code ([b444908](https://github.com/jjack/hass-remote-boot-manager/commit/b4449082f158c16fe2ef7da2199d67607a861985))
* better handlig of custom types ([0ed7f4c](https://github.com/jjack/hass-remote-boot-manager/commit/0ed7f4c1f73ea8319755dcf1cc2c138b9d057501))
* better handling an empty os list ([6295d92](https://github.com/jjack/hass-remote-boot-manager/commit/6295d923d94a4e196fa16dc792cab4196ac102c2))
* better handling of missing json ([e8ff2b2](https://github.com/jjack/hass-remote-boot-manager/commit/e8ff2b26f79ea8c87df8e611bcc602ee500e863c))
* can now select an OS for real ([1d3121a](https://github.com/jjack/hass-remote-boot-manager/commit/1d3121a0a28f4938bd26e4fb6a2b8b8a54eb070e))
* consuming boot config so that it doesn't persist ([db3d405](https://github.com/jjack/hass-remote-boot-manager/commit/db3d405f2727fc37532fbe00f963338a2f2b89a3))
* correcting the remote-boot-agent url ([7240ca3](https://github.com/jjack/hass-remote-boot-manager/commit/7240ca31027a8ee53b0952cd3c77ce72a11d5f07))
* defaults is not default ([6263aac](https://github.com/jjack/hass-remote-boot-manager/commit/6263aace39069aaa1ec46da19aa152a66f2f631a))
* dropping the homeassistant package down even more, because it's the latest available in the CI ([b877c4d](https://github.com/jjack/hass-remote-boot-manager/commit/b877c4dcf1560a43a14ca5b226a093dd627901fb))
* ensuring mac address is present in the bootloader get request ([aa1370c](https://github.com/jjack/hass-remote-boot-manager/commit/aa1370c414337a63382d4a995c521f2703b73856))
* fixing documentation url in config flow ([7aebc00](https://github.com/jjack/hass-remote-boot-manager/commit/7aebc00837e12cf9224e13a98d237fe83123ff98))
* fixing hostname in device info ([0f1f720](https://github.com/jjack/hass-remote-boot-manager/commit/0f1f7209392d74407a15df32654f20059bc59752))
* fixing issue with test and possible None values ([56a0d45](https://github.com/jjack/hass-remote-boot-manager/commit/56a0d45bb997f86935dcbb449ae02bdd4f41b12c))
* fixing log message variable ([3945939](https://github.com/jjack/hass-remote-boot-manager/commit/3945939dab23e5d97b30b9551c805bab4654a31b))
* fixing sync/async handling of bootloaders ([1139e59](https://github.com/jjack/hass-remote-boot-manager/commit/1139e590fa1b13eff53bdf2c1d6a348f4f080548))
* handling new/old servers a little differently ([28d4131](https://github.com/jjack/hass-remote-boot-manager/commit/28d41317212211288df66a4ba4196cedcf0835d5))
* linting and adding missing wakeonlan dependency ([8fdf601](https://github.com/jjack/hass-remote-boot-manager/commit/8fdf6017247edcf04bf00e4ebd381fad186c35e2))
* no longer consuming the next boot option immediately so that it can actually get picked up in the boot process ([1d11478](https://github.com/jjack/hass-remote-boot-manager/commit/1d11478da655aca53a15a1f1a8920d3213e941f1))
* normalizing mac addresses ([9308f2c](https://github.com/jjack/hass-remote-boot-manager/commit/9308f2ce5cd6de897aef7059ed0d0c8e6883bfd0))
* registering/unregistering views to prevent memory issues ([9a30b83](https://github.com/jjack/hass-remote-boot-manager/commit/9a30b83a66fafcba21ffeadaab1eaefbfd0b0d2f))
* removing busted is_new logic ([7713d05](https://github.com/jjack/hass-remote-boot-manager/commit/7713d05a2688f00da23f20010af6e0bdff0f8bc5))
* removing busted is_new logic for servers ([beb6e83](https://github.com/jjack/hass-remote-boot-manager/commit/beb6e83a55c1ff0d88a85cd5e7eba83dada8e35d))
* reset the OS when the button gets pressed ([6d97571](https://github.com/jjack/hass-remote-boot-manager/commit/6d975717584feecd7ff76a9153273a76eb7097c9))
* saving boot manager state across hass restarts ([ca4de54](https://github.com/jjack/hass-remote-boot-manager/commit/ca4de54765d1a64a55fbddd95c7bf3c8c7226783))
* this hasn't been called netboot manager in a while ([55fafbc](https://github.com/jjack/hass-remote-boot-manager/commit/55fafbcd741d825e52003d2e27b110dca2c8c4e9))
* updating ha device registry when hostnames change ([35dce1e](https://github.com/jjack/hass-remote-boot-manager/commit/35dce1e2be7597cf6a7d0745059dc4acdc7fc66a))
* updating issue_tracker string to the correct url ([c47f7b6](https://github.com/jjack/hass-remote-boot-manager/commit/c47f7b62b10275712e49d06a346c7387bd6e2add))
* updating manager to handle the incoming webhook ([62ce29a](https://github.com/jjack/hass-remote-boot-manager/commit/62ce29a93d79e3749e5dbf54300ba1be62fb728b))
* using .venv ruff command for linting ([9f96b65](https://github.com/jjack/hass-remote-boot-manager/commit/9f96b6583dde923367c0aff87101e9d3f5419f4e))
* using correct act location for github local actions ([19f5356](https://github.com/jjack/hass-remote-boot-manager/commit/19f53567b97d3710aef012bbfe05253d4270e097))
* using correct name for boot config generation ([10107a2](https://github.com/jjack/hass-remote-boot-manager/commit/10107a2027f7da9150027755b13a0818d2f5b43d))
* using working version of homeassistant package ([31e7534](https://github.com/jjack/hass-remote-boot-manager/commit/31e7534ebe968a5ca63b4f5006eb3197d84b5be6))

## [0.3.1](https://github.com/jjack/hass-remote-boot-manager/compare/v0.3.0...v0.3.1) (2026-04-29)


### Bug Fixes

* defaults is not default ([6263aac](https://github.com/jjack/hass-remote-boot-manager/commit/6263aace39069aaa1ec46da19aa152a66f2f631a))

## [0.3.0](https://github.com/jjack/hass-remote-boot-manager/compare/v0.2.0...v0.3.0) (2026-04-29)


### Features

* adding broadcast address and port ([54e1695](https://github.com/jjack/hass-remote-boot-manager/commit/54e16951145b96fcfe9718fa233eda235e145898))
* can regenerate the webhook id ([421820a](https://github.com/jjack/hass-remote-boot-manager/commit/421820abb57eee7388345acad3481c1b12ef819e))


### Bug Fixes

* correcting the remote-boot-agent url ([7240ca3](https://github.com/jjack/hass-remote-boot-manager/commit/7240ca31027a8ee53b0952cd3c77ce72a11d5f07))

## [0.2.0](https://github.com/jjack/hass-remote-boot-manager/compare/v0.1.1...v0.2.0) (2026-04-16)


### Features

* adding release please for release versioning ([b509f8a](https://github.com/jjack/hass-remote-boot-manager/commit/b509f8ace50acec9be792220bf24ad3ffc8f8636))
* allowing a custom webhook id ([20e2319](https://github.com/jjack/hass-remote-boot-manager/commit/20e2319bff2a8dfe56471e352479dd1abf5724db))
* can now auto-generate webhook_ids for security ([f8d94e3](https://github.com/jjack/hass-remote-boot-manager/commit/f8d94e36565dc95508262327519b058bf3148285))
* home assistant now starts and lets me almost add the integration ([478848e](https://github.com/jjack/hass-remote-boot-manager/commit/478848efedd8ef9ad5b2f53e918cee25f88d91cc))


### Bug Fixes

* adding missing wakeonlan dependency ([23f5114](https://github.com/jjack/hass-remote-boot-manager/commit/23f51140726e3b7311e74b90ff694fbd7ca6e022))
* adding new platforms and removing dead code ([b444908](https://github.com/jjack/hass-remote-boot-manager/commit/b4449082f158c16fe2ef7da2199d67607a861985))
* better handlig of custom types ([0ed7f4c](https://github.com/jjack/hass-remote-boot-manager/commit/0ed7f4c1f73ea8319755dcf1cc2c138b9d057501))
* better handling an empty os list ([6295d92](https://github.com/jjack/hass-remote-boot-manager/commit/6295d923d94a4e196fa16dc792cab4196ac102c2))
* better handling of missing json ([e8ff2b2](https://github.com/jjack/hass-remote-boot-manager/commit/e8ff2b26f79ea8c87df8e611bcc602ee500e863c))
* can now select an OS for real ([1d3121a](https://github.com/jjack/hass-remote-boot-manager/commit/1d3121a0a28f4938bd26e4fb6a2b8b8a54eb070e))
* consuming boot config so that it doesn't persist ([db3d405](https://github.com/jjack/hass-remote-boot-manager/commit/db3d405f2727fc37532fbe00f963338a2f2b89a3))
* dropping the homeassistant package down even more, because it's the latest available in the CI ([b877c4d](https://github.com/jjack/hass-remote-boot-manager/commit/b877c4dcf1560a43a14ca5b226a093dd627901fb))
* ensuring mac address is present in the bootloader get request ([aa1370c](https://github.com/jjack/hass-remote-boot-manager/commit/aa1370c414337a63382d4a995c521f2703b73856))
* fixing documentation url in config flow ([7aebc00](https://github.com/jjack/hass-remote-boot-manager/commit/7aebc00837e12cf9224e13a98d237fe83123ff98))
* fixing hostname in device info ([0f1f720](https://github.com/jjack/hass-remote-boot-manager/commit/0f1f7209392d74407a15df32654f20059bc59752))
* fixing issue with test and possible None values ([56a0d45](https://github.com/jjack/hass-remote-boot-manager/commit/56a0d45bb997f86935dcbb449ae02bdd4f41b12c))
* fixing log message variable ([3945939](https://github.com/jjack/hass-remote-boot-manager/commit/3945939dab23e5d97b30b9551c805bab4654a31b))
* fixing sync/async handling of bootloaders ([1139e59](https://github.com/jjack/hass-remote-boot-manager/commit/1139e590fa1b13eff53bdf2c1d6a348f4f080548))
* handling new/old servers a little differently ([28d4131](https://github.com/jjack/hass-remote-boot-manager/commit/28d41317212211288df66a4ba4196cedcf0835d5))
* linting and adding missing wakeonlan dependency ([8fdf601](https://github.com/jjack/hass-remote-boot-manager/commit/8fdf6017247edcf04bf00e4ebd381fad186c35e2))
* no longer consuming the next boot option immediately so that it can actually get picked up in the boot process ([1d11478](https://github.com/jjack/hass-remote-boot-manager/commit/1d11478da655aca53a15a1f1a8920d3213e941f1))
* normalizing mac addresses ([9308f2c](https://github.com/jjack/hass-remote-boot-manager/commit/9308f2ce5cd6de897aef7059ed0d0c8e6883bfd0))
* registering/unregistering views to prevent memory issues ([9a30b83](https://github.com/jjack/hass-remote-boot-manager/commit/9a30b83a66fafcba21ffeadaab1eaefbfd0b0d2f))
* removing busted is_new logic ([7713d05](https://github.com/jjack/hass-remote-boot-manager/commit/7713d05a2688f00da23f20010af6e0bdff0f8bc5))
* removing busted is_new logic for servers ([beb6e83](https://github.com/jjack/hass-remote-boot-manager/commit/beb6e83a55c1ff0d88a85cd5e7eba83dada8e35d))
* reset the OS when the button gets pressed ([6d97571](https://github.com/jjack/hass-remote-boot-manager/commit/6d975717584feecd7ff76a9153273a76eb7097c9))
* saving boot manager state across hass restarts ([ca4de54](https://github.com/jjack/hass-remote-boot-manager/commit/ca4de54765d1a64a55fbddd95c7bf3c8c7226783))
* this hasn't been called netboot manager in a while ([55fafbc](https://github.com/jjack/hass-remote-boot-manager/commit/55fafbcd741d825e52003d2e27b110dca2c8c4e9))
* updating ha device registry when hostnames change ([35dce1e](https://github.com/jjack/hass-remote-boot-manager/commit/35dce1e2be7597cf6a7d0745059dc4acdc7fc66a))
* updating issue_tracker string to the correct url ([c47f7b6](https://github.com/jjack/hass-remote-boot-manager/commit/c47f7b62b10275712e49d06a346c7387bd6e2add))
* updating manager to handle the incoming webhook ([62ce29a](https://github.com/jjack/hass-remote-boot-manager/commit/62ce29a93d79e3749e5dbf54300ba1be62fb728b))
* using .venv ruff command for linting ([9f96b65](https://github.com/jjack/hass-remote-boot-manager/commit/9f96b6583dde923367c0aff87101e9d3f5419f4e))
* using correct act location for github local actions ([19f5356](https://github.com/jjack/hass-remote-boot-manager/commit/19f53567b97d3710aef012bbfe05253d4270e097))
* using correct name for boot config generation ([10107a2](https://github.com/jjack/hass-remote-boot-manager/commit/10107a2027f7da9150027755b13a0818d2f5b43d))
* using working version of homeassistant package ([31e7534](https://github.com/jjack/hass-remote-boot-manager/commit/31e7534ebe968a5ca63b4f5006eb3197d84b5be6))


### Documentation

* added README ([2d07d3c](https://github.com/jjack/hass-remote-boot-manager/commit/2d07d3c5e525bd58a4e42f0cfc8861e90b21afa2))
* correcting webhook id display ([77b701e](https://github.com/jjack/hass-remote-boot-manager/commit/77b701e8ad22f5ade971f3a027ede7bee9ec5ec8))
